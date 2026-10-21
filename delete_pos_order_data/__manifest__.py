# -*- coding: utf-8 -*-
{
    'name': 'Delete Point of Sale Order Data',
    'version': '15.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Module untuk menghapus data Point of Sale Orders dan transaksi order terkait di Accounting dan Stock',
    'description': """
Delete Point of Sale Order Data
===============================
Modul khusus Odoo 15 untuk menghapus data Orders Point of Sale secara fleksibel beserta:
- Transaksi Journal Entry (Account Move) di Accounting
- Stock Picking & Stock Move di Inventory
- POS Payments
    """,
    'author': 'Developer',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'account',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/delete_pos_order_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
