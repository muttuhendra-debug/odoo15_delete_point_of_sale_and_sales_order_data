# -*- coding: utf-8 -*-

from datetime import datetime, time
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DeletePosOrderWizard(models.TransientModel):
    _name = 'delete.pos.order.wizard'
    _description = 'Delete Point of Sale Order Data Wizard'

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    pos_config_ids = fields.Many2many(
        'pos.config',
        string='Point of Sale'
    )
    pos_session_ids = fields.Many2many(
        'pos.session',
        string='POS Sessions'
    )
    pos_order_ids = fields.Many2many(
        'pos.order',
        string='Specific POS Orders'
    )
    delete_accounting_entries = fields.Boolean(
        string='Delete Journal Entries (Accounting)',
        default=True,
        help='If checked, posted account move entries linked to the POS orders will be cancelled and deleted.'
    )
    delete_stock_moves = fields.Boolean(
        string='Delete Stock Picking & Moves',
        default=True,
        help='If checked, stock pickings and stock moves linked to the POS orders will be cancelled and deleted.'
    )
    delete_payments = fields.Boolean(
        string='Delete POS Payments',
        default=True,
        help='If checked, payment records associated with the POS orders will be deleted.'
    )
    use_fast_mode = fields.Boolean(
        string='Fast SQL Mode (High Performance)',
        default=True,
        help='Uses direct database batch deletion for fast execution on large datasets (~100x faster).'
    )
    batch_size = fields.Integer(
        string='Batch Size',
        default=500,
        help='Number of orders to process per database commit batch (Recommended: 100 - 1000).'
    )

    def action_delete_pos_orders(self):
        self.ensure_one()

        if self.pos_order_ids:
            order_ids = self.pos_order_ids.ids
        else:
            domain = []
            if self.start_date:
                start_dt = datetime.combine(self.start_date, time.min)
                domain.append(('date_order', '>=', start_dt))
            if self.end_date:
                end_dt = datetime.combine(self.end_date, time.max)
                domain.append(('date_order', '<=', end_dt))
            if self.pos_config_ids:
                domain.append(('config_id', 'in', self.pos_config_ids.ids))
            if self.pos_session_ids:
                domain.append(('session_id', 'in', self.pos_session_ids.ids))

            order_ids = self.env['pos.order'].search(domain).ids

        if not order_ids:
            raise UserError(_("No POS Orders found matching the specified criteria."))

        total_orders = len(order_ids)
        batch_sz = self.batch_size if self.batch_size and self.batch_size > 0 else 500

        if self.use_fast_mode:
            self._delete_fast_sql_mode(order_ids, batch_sz)
        else:
            self._delete_orm_mode(order_ids, batch_sz)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Successfully deleted %s POS Order(s) and associated data.') % total_orders,
                'type': 'success',
                'sticky': False,
            }
        }

    def _delete_fast_sql_mode(self, order_ids, batch_sz):
        cr = self.env.cr

        for i in range(0, len(order_ids), batch_sz):
            batch_order_ids = tuple(order_ids[i:i + batch_sz])

            # Get linked move IDs if delete accounting entries is requested
            move_ids = []
            if self.delete_accounting_entries:
                cr.execute("SELECT DISTINCT account_move FROM pos_order WHERE id IN %s AND account_move IS NOT NULL", (batch_order_ids,))
                move_ids = [r[0] for r in cr.fetchall()]

            # 1. Delete Stock Pickings & Moves if checked
            if self.delete_stock_moves:
                cr.execute("SELECT id FROM stock_picking WHERE pos_order_id IN %s", (batch_order_ids,))
                picking_ids = [r[0] for r in cr.fetchall()]
                if picking_ids:
                    pick_tuple = tuple(picking_ids)
                    cr.execute("SELECT id FROM stock_move WHERE picking_id IN %s", (pick_tuple,))
                    sm_ids = [r[0] for r in cr.fetchall()]
                    if sm_ids:
                        sm_tuple = tuple(sm_ids)
                        cr.execute("DELETE FROM stock_valuation_layer WHERE stock_move_id IN %s", (sm_tuple,))
                        cr.execute("DELETE FROM stock_move_line WHERE move_id IN %s", (sm_tuple,))
                        cr.execute("DELETE FROM stock_move WHERE id IN %s", (sm_tuple,))
                    cr.execute("DELETE FROM stock_move_line WHERE picking_id IN %s", (pick_tuple,))
                    cr.execute("DELETE FROM stock_picking WHERE id IN %s", (pick_tuple,))

            # 2. Delete POS Payments (Always delete payments linked to POS orders to satisfy FK constraints)
            cr.execute("DELETE FROM pos_payment WHERE pos_order_id IN %s", (batch_order_ids,))

            # 3. Clean up pack operation lot records
            cr.execute("SELECT id FROM pos_order_line WHERE order_id IN %s", (batch_order_ids,))
            pol_ids = [r[0] for r in cr.fetchall()]
            if pol_ids:
                pol_tuple = tuple(pol_ids)
                cr.execute("DELETE FROM pos_pack_operation_lot WHERE pos_order_line_id IN %s", (pol_tuple,))

            # 4. Delete POS Order Lines
            cr.execute("DELETE FROM pos_order_line WHERE order_id IN %s", (batch_order_ids,))

            # 5. Clear FK references on pos_order before deleting account_move
            cr.execute("UPDATE pos_order SET account_move = NULL WHERE id IN %s", (batch_order_ids,))

            # 6. Delete POS Orders
            cr.execute("DELETE FROM pos_order WHERE id IN %s", (batch_order_ids,))

            # 7. Delete Journal Entries
            if self.delete_accounting_entries and move_ids:
                move_tuple = tuple(move_ids)
                cr.execute("DELETE FROM stock_valuation_layer WHERE account_move_id IN %s", (move_tuple,))
                cr.execute("SELECT id FROM account_move_line WHERE move_id IN %s", (move_tuple,))
                aml_ids = [r[0] for r in cr.fetchall()]
                if aml_ids:
                    aml_tuple = tuple(aml_ids)
                    cr.execute("DELETE FROM account_analytic_line WHERE move_line_id IN %s", (aml_tuple,))
                    cr.execute("DELETE FROM account_partial_reconcile WHERE debit_move_id IN %s OR credit_move_id IN %s", (aml_tuple, aml_tuple))
                    cr.execute("UPDATE account_move_line SET full_reconcile_id = NULL WHERE id IN %s", (aml_tuple,))
                    cr.execute("DELETE FROM account_move_line WHERE move_id IN %s", (move_tuple,))
                cr.execute("DELETE FROM account_move WHERE id IN %s", (move_tuple,))

            # Commit batch transaction to release locks and prevent timeouts
            self.env.cr.commit()

        # Invalidate ORM cache in Odoo 15
        self.env.clear()

    def _delete_orm_mode(self, order_ids, batch_sz):
        PosOrder = self.env['pos.order']
        cr = self.env.cr

        def _delete_moves(moves):
            moves = moves.filtered(lambda m: m.exists())
            if not moves:
                return
            reconciled_lines = moves.mapped('line_ids').filtered(
                lambda l: l.reconciled or l.full_reconcile_id or l.matched_debit_ids or l.matched_credit_ids
            )
            if reconciled_lines:
                reconciled_lines.remove_move_reconcile()
            for move in moves:
                if move.state != 'draft':
                    move.button_draft()
            moves.with_context(force_delete=True).unlink()

        for i in range(0, len(order_ids), batch_sz):
            batch_ids = order_ids[i:i + batch_sz]
            orders = PosOrder.browse(batch_ids).filtered(lambda o: o.exists())

            if self.delete_accounting_entries:
                moves = orders.mapped('account_move').filtered(lambda m: m.exists())
                _delete_moves(moves)

            if self.delete_stock_moves:
                pickings = orders.mapped('picking_ids').filtered(lambda p: p.exists())
                if pickings:
                    moves = pickings.mapped('move_lines').filtered(lambda m: m.exists())
                    if moves:
                        cr.execute("UPDATE stock_move SET state='draft' WHERE id IN %s", (tuple(moves.ids),))
                        moves.with_context(force_delete=True).unlink()
                    cr.execute("UPDATE stock_picking SET state='draft' WHERE id IN %s", (tuple(pickings.ids),))
                    pickings.with_context(force_delete=True).unlink()

            payments = orders.mapped('payment_ids').filtered(lambda p: p.exists())
            if payments:
                payments.unlink()

            orders.write({'state': 'draft'})
            orders.unlink()

            self.env.cr.commit()
