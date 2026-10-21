# -*- coding: utf-8 -*-

from datetime import datetime, time
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DeletePosOrderWizard(models.TransientModel):
    _name = 'delete.pos.order.wizard'
    _description = 'Delete Point of Sale Order Data Wizard'

    filter_type = fields.Selection([
        ('date_range', 'Date Range'),
        ('month', 'By Month & Year'),
    ], string='Filter Type', default='date_range')

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month', default=lambda self: str(fields.Date.today().month))

    year = fields.Integer(string='Year', default=lambda self: fields.Date.today().year)
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
        help='Number of orders to process per batch step (Recommended: 100 - 1000).'
    )

    # Progress tracking fields
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('done', 'Completed')
    ], string='Status', default='draft')
    total_count = fields.Integer(string='Total Orders', default=0)
    deleted_count = fields.Integer(string='Deleted Orders', default=0)
    progress_percent = fields.Float(string='Progress (%)', default=0.0)
    remaining_order_ids = fields.Text(string='Remaining Order IDs')

    def action_start_deletion(self):
        self.ensure_one()

        if self.pos_order_ids:
            order_ids = self.pos_order_ids.ids
        else:
            domain = []
            if self.filter_type == 'month' and self.month and self.year:
                import calendar
                m = int(self.month)
                y = int(self.year)
                last_day = calendar.monthrange(y, m)[1]
                s_date = datetime(y, m, 1)
                e_date = datetime(y, m, last_day, 23, 59, 59)
                domain.append(('date_order', '>=', s_date))
                domain.append(('date_order', '<=', e_date))
            else:
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

        self.write({
            'state': 'processing',
            'total_count': len(order_ids),
            'deleted_count': 0,
            'progress_percent': 0.0,
            'remaining_order_ids': json.dumps(order_ids),
        })

        return self.action_process_next_batch()

    def action_process_next_batch(self):
        self.ensure_one()
        if self.state != 'processing' or not self.remaining_order_ids:
            return self._reopen_wizard()

        try:
            remaining_ids = json.loads(self.remaining_order_ids)
        except Exception:
            remaining_ids = []

        if not remaining_ids:
            self.write({
                'state': 'done',
                'progress_percent': 100.0,
            })
            return self._reopen_wizard()

        batch_sz = self.batch_size if self.batch_size and self.batch_size > 0 else 500
        current_batch_ids = remaining_ids[:batch_sz]
        next_remaining_ids = remaining_ids[batch_sz:]

        if self.use_fast_mode:
            self._delete_fast_sql_batch(current_batch_ids)
        else:
            self._delete_orm_batch(current_batch_ids)

        new_deleted_count = self.deleted_count + len(current_batch_ids)
        new_progress = min(100.0, round((new_deleted_count / self.total_count) * 100.0, 2)) if self.total_count else 100.0
        new_state = 'done' if not next_remaining_ids else 'processing'

        self.write({
            'state': new_state,
            'deleted_count': new_deleted_count,
            'progress_percent': new_progress,
            'remaining_order_ids': json.dumps(next_remaining_ids),
        })

        return self._reopen_wizard()

    def action_process_all_remaining(self):
        self.ensure_one()
        if self.state != 'processing' or not self.remaining_order_ids:
            return self._reopen_wizard()

        try:
            remaining_ids = json.loads(self.remaining_order_ids)
        except Exception:
            remaining_ids = []

        if not remaining_ids:
            self.write({
                'state': 'done',
                'progress_percent': 100.0,
            })
            return self._reopen_wizard()

        batch_sz = self.batch_size if self.batch_size and self.batch_size > 0 else 2000
        while remaining_ids:
            current_batch_ids = remaining_ids[:batch_sz]
            remaining_ids = remaining_ids[batch_sz:]

            if self.use_fast_mode:
                self._delete_fast_sql_batch(current_batch_ids)
            else:
                self._delete_orm_batch(current_batch_ids)

            new_deleted_count = self.deleted_count + len(current_batch_ids)
            new_progress = min(100.0, round((new_deleted_count / self.total_count) * 100.0, 2)) if self.total_count else 100.0
            new_state = 'done' if not remaining_ids else 'processing'

            self.write({
                'state': new_state,
                'deleted_count': new_deleted_count,
                'progress_percent': new_progress,
                'remaining_order_ids': json.dumps(remaining_ids),
            })
            self.env.cr.commit()

        return self._reopen_wizard()

    def _reopen_wizard(self):
        return {
            'name': _('Delete Point of Sale Order Data'),
            'type': 'ir.actions.act_window',
            'res_model': 'delete.pos.order.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _delete_fast_sql_batch(self, batch_order_ids):
        cr = self.env.cr
        batch_tuple = tuple(batch_order_ids)

        # Get linked move IDs if delete accounting entries is requested
        move_ids = []
        if self.delete_accounting_entries:
            cr.execute("SELECT DISTINCT account_move FROM pos_order WHERE id IN %s AND account_move IS NOT NULL", (batch_tuple,))
            move_ids = [r[0] for r in cr.fetchall()]

        # 1. Delete Stock Pickings & Moves if checked
        if self.delete_stock_moves:
            cr.execute("SELECT id FROM stock_picking WHERE pos_order_id IN %s", (batch_tuple,))
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
        cr.execute("DELETE FROM pos_payment WHERE pos_order_id IN %s", (batch_tuple,))

        # 3. Clean up pack operation lot records
        cr.execute("SELECT id FROM pos_order_line WHERE order_id IN %s", (batch_tuple,))
        pol_ids = [r[0] for r in cr.fetchall()]
        if pol_ids:
            pol_tuple = tuple(pol_ids)
            cr.execute("DELETE FROM pos_pack_operation_lot WHERE pos_order_line_id IN %s", (pol_tuple,))

        # 4. Delete POS Order Lines
        cr.execute("DELETE FROM pos_order_line WHERE order_id IN %s", (batch_tuple,))

        # 5. Clear FK references on pos_order before deleting account_move
        cr.execute("UPDATE pos_order SET account_move = NULL WHERE id IN %s", (batch_tuple,))

        # 6. Delete POS Orders
        cr.execute("DELETE FROM pos_order WHERE id IN %s", (batch_tuple,))

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

        self.env.cr.commit()
        self.env.clear()

    def _delete_orm_batch(self, batch_ids):
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
