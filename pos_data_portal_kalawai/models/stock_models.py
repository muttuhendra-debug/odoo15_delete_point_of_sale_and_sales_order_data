from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    qty_available = fields.Float(store=True)

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    quantity = fields.Float(store=True)
    inventory_quantity = fields.Float(store=True)

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    quantity = fields.Float(store=True)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    qty_done = fields.Float(store=True)
