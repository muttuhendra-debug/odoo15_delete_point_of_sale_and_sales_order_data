from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError

class POSDeleteData(models.Model):
    _name = 'kalawai.pos.data.deletion'

    name = fields.Char('Dihapus Oleh')
    tahun_data = fields.Selection([
        ('2017', '2017'),
        ('2018', '2018'),
        ('2019', '2019'),
        ('2020', '2020'),
        ('2021', '2021'),
        ('2022', '2022'),
        ('2023', '2023'),
        ('2024', '2024'),
        ('2025', '2025'),
    ], string='Dibawah Tahun')
    is_accounting_permissed = fields.Boolean(string='Sudah Mendapatkan Ijin dari Bagian Akuntansi')
    is_sales_permissed = fields.Boolean(string='Sudah Mendapatkan Ijin dari Bagian Penjualan')
    is_purchase_permissed = fields.Boolean(string='Sudah Mendapatkan Ijin dari Bagian Pembelian/Gudang')
    data_del_type = fields.Selection([
        ('pos', 'Penjualan Kasir'),
        ('po', 'Pembelian Gudang'),
        ('stock', 'Stok Barang Ditangan')
    ], stating='Jenis Data')

    def delete_data_pos_order(self):
        if self.is_accounting_permissed and self.is_sales_permissed:
            self.ensure_one()  # Ensure that the method operates on a single record

            # Check if data exists for the specified year
            query_check_data = f'''
                SELECT COUNT(*) FROM pos_order
                WHERE date_order < '{self.tahun_data}-12-31';
            '''
            self.env.cr.execute(query_check_data)
            data_count = self.env.cr.fetchone()[0]

            if data_count == 0:
                raise ValidationError(f"Data Pada Tahun {self.tahun_data} Tidak Tersedia!")

            query_disable_constraint = 'ALTER TABLE pos_order DISABLE TRIGGER ALL;'
            query_main = f'''
                DELETE FROM pos_order
                WHERE date_order < '{self.tahun_data}-12-31'
                RETURNING id;
            '''
            query_enable_constraint = 'ALTER TABLE pos_order ENABLE TRIGGER ALL;'

            try:
                # Execute queries sequentially
                self.env.cr.execute(query_disable_constraint)
                self.env.cr.execute(query_main)
                deleted_records = self.env.cr.fetchall()
                deleted_count = len(deleted_records)
                self.env.cr.execute(query_enable_constraint)
            except Exception as e:
                raise UserError(f"Terjadi kesalahan selama penghapusan data: {str(e)}")

            # Return success message with deleted count
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Berhasil',
                    'message': f'Penghapusan Data Berhasil! Total data terhapus: {deleted_count}',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise ValidationError('Anda tidak berhak menghapus data penjualan POS Kalawai Mart!')

    def delete_data_purchase_order(self):
        if self.is_accounting_permissed and self.is_purchase_permissed:
            self.ensure_one()

            query_check_data = f'''
                SELECT COUNT(*) FROM purchase_order
                WHERE date_order < '{self.tahun_data}-12-31';
            '''
            self.env.cr.execute(query_check_data)
            data_count = self.env.cr.fetchone()[0]

            if data_count == 0:
                raise ValidationError(f"Data Pada Tahun {self.tahun_data} Tidak Tersedia!")

            query_disable_constraint = 'ALTER TABLE purchase_order DISABLE TRIGGER ALL;'
            query_main = f'''
                DELETE FROM purchase_order
                WHERE date_order < '{self.tahun_data}-12-31'
                RETURNING id;
            '''
            query_enable_constraint = 'ALTER TABLE purchase_order ENABLE TRIGGER ALL;'

            try:
                self.env.cr.execute(query_disable_constraint)
                self.env.cr.execute(query_main)
                deleted_records = self.env.cr.fetchall()
                deleted_count = len(deleted_records)
                self.env.cr.execute(query_enable_constraint)
            except Exception as e:
                raise UserError(f"Terjadi kesalahan selama penghapusan data: {str(e)}")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Berhasil',
                    'message': f'Penghapusan Data Berhasil! Total data terhapus: {deleted_count}',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise ValidationError('Anda tidak berhak menghapus data Purchase Order Kalawai Mart!')

    # def update_data_onhand_stock(self):
    #     if self.is_purchase_permissed:
    #         self.ensure_one()

    #         # Confirm that there is data in the relevant tables
    #         queries_to_check = {
    #             'product_template': "SELECT COUNT(*) FROM product_template WHERE qty_available > 0.0",
    #             'stock_quant': "SELECT COUNT(*) FROM stock_quant WHERE quantity > 0.0",
    #             'stock_valuation_layer': "SELECT COUNT(*) FROM stock_valuation_layer WHERE quantity > 0.0",
    #             'stock_move_line': "SELECT COUNT(*) FROM stock_move_line WHERE qty_done > 0.0",
    #             'stock_picking': "SELECT COUNT(*) FROM stock_picking",
    #         }
            
    #         data_count = 0
    #         for table, query in queries_to_check.items():
    #             self.env.cr.execute(query)
    #             data_count += self.env.cr.fetchone()[0]
            
    #         if data_count == 0:
    #             raise ValidationError("Tidak ada stok tersedia untuk dihapus!")

    #         # Prepare individual update queries
    #         update_queries = [
    #             "UPDATE product_template SET qty_available = 0.0",
    #             "UPDATE stock_quant SET quantity = 0.0, inventory_quantity = 0.0",
    #             "UPDATE stock_valuation_layer SET quantity = 0.0",
    #             "UPDATE stock_move_line SET qty_done = 0.0",
    #         ]

    #         truncate_query = "TRUNCATE TABLE stock_picking CASCADE"

    #         # Disable triggers
    #         disable_trigger_queries = [
    #             "ALTER TABLE product_template DISABLE TRIGGER ALL",
    #             "ALTER TABLE stock_quant DISABLE TRIGGER ALL",
    #             "ALTER TABLE stock_valuation_layer DISABLE TRIGGER ALL",
    #             "ALTER TABLE stock_move_line DISABLE TRIGGER ALL",
    #             "ALTER TABLE stock_picking DISABLE TRIGGER ALL",
    #         ]

    #         # Enable triggers
    #         enable_trigger_queries = [
    #             "ALTER TABLE product_template ENABLE TRIGGER ALL",
    #             "ALTER TABLE stock_quant ENABLE TRIGGER ALL",
    #             "ALTER TABLE stock_valuation_layer ENABLE TRIGGER ALL",
    #             "ALTER TABLE stock_move_line ENABLE TRIGGER ALL",
    #             "ALTER TABLE stock_picking ENABLE TRIGGER ALL",
    #         ]

    #         try:
    #             # Disable triggers
    #             for query in disable_trigger_queries:
    #                 self.env.cr.execute(query)

    #             # Execute updates
    #             for query in update_queries:
    #                 self.env.cr.execute(query)
                
    #             # Truncate stock_picking
    #             self.env.cr.execute(truncate_query)

    #             # Enable triggers
    #             for query in enable_trigger_queries:
    #                 self.env.cr.execute(query)

    #         except Exception as e:
    #             raise UserError(f"Terjadi kesalahan selama pengosongan data stok: {str(e)}")

    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': 'Berhasil',
    #                 'message': 'Pengosongan data stok berhasil! Semua stok sekarang kosong.',
    #                 'type': 'success',
    #                 'sticky': False,
    #             }
    #         }
    #     else:
    #         raise ValidationError('Anda tidak berhak menghapus data Stok Persediaan Kalawai Mart!')

    #     def unlink(self):
    #         if not self.env.user.has_group('base.group_system'):
    #             raise AccessError(_("Anda tidak berhak untuk menghapus riwayat penghapusan data Kalawai, silakan hubungi Administrator!"))
    #         return super(POSDeleteData, self).unlink()

    def update_data_onhand_stock(self):
        """
        Safely clears stock-related data while preserving data integrity and avoiding critical cascades.
        """
        if self.is_purchase_permissed:
            self.ensure_one()

            # Confirm that there is data in the relevant tables
            queries_to_check = {
                'product_template': "SELECT COUNT(*) FROM product_template WHERE qty_available > 0.0",
                'stock_quant': "SELECT COUNT(*) FROM stock_quant WHERE quantity > 0.0",
                'stock_valuation_layer': "SELECT COUNT(*) FROM stock_valuation_layer WHERE quantity > 0.0",
                'stock_move_line': "SELECT COUNT(*) FROM stock_move_line WHERE qty_done > 0.0",
            }

            data_count = 0
            for table, query in queries_to_check.items():
                self.env.cr.execute(query)
                data_count += self.env.cr.fetchone()[0]

            if data_count == 0:
                raise ValidationError("Tidak ada stok tersedia untuk dihapus!")

            # Prepare individual update queries
            update_queries = [
                "UPDATE product_template SET qty_available = 0.0",
                "UPDATE stock_quant SET quantity = 0.0, inventory_quantity = 0.0",
                "UPDATE stock_valuation_layer SET quantity = 0.0",
                "UPDATE stock_move_line SET qty_done = 0.0",
            ]

            # Disable triggers
            disable_trigger_queries = [
                "ALTER TABLE product_template DISABLE TRIGGER ALL",
                "ALTER TABLE stock_quant DISABLE TRIGGER ALL",
                "ALTER TABLE stock_valuation_layer DISABLE TRIGGER ALL",
                "ALTER TABLE stock_move_line DISABLE TRIGGER ALL",
            ]

            # Enable triggers
            enable_trigger_queries = [
                "ALTER TABLE product_template ENABLE TRIGGER ALL",
                "ALTER TABLE stock_quant ENABLE TRIGGER ALL",
                "ALTER TABLE stock_valuation_layer ENABLE TRIGGER ALL",
                "ALTER TABLE stock_move_line ENABLE TRIGGER ALL",
            ]

            try:
                with self.env.cr.savepoint():
                    # Disable triggers
                    for query in disable_trigger_queries:
                        self.env.cr.execute(query)

                    # Execute updates
                    for query in update_queries:
                        self.env.cr.execute(query)

                    # Enable triggers
                    for query in enable_trigger_queries:
                        self.env.cr.execute(query)

            except Exception as e:
                # Ensure triggers are re-enabled even if an error occurs
                for query in enable_trigger_queries:
                    self.env.cr.execute(query)
                raise UserError(f"Terjadi kesalahan selama pengosongan data stok: {str(e)}")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Berhasil',
                    'message': 'Pengosongan data stok berhasil! Semua stok sekarang kosong.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise ValidationError('Anda tidak berhak menghapus data Stok Persediaan Kalawai Mart!')

    def unlink(self):
        """
        Prevent unauthorized deletion of data cleaner records.
        """
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Anda tidak berhak untuk menghapus riwayat penghapusan data Kalawai, silakan hubungi Administrator!"))
        return super(StockDataCleaner, self).unlink()


