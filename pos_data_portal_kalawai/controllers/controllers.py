# -*- coding: utf-8 -*-
# from odoo import http


# class PosDataPortalKalawai(http.Controller):
#     @http.route('/pos_data_portal_kalawai/pos_data_portal_kalawai', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pos_data_portal_kalawai/pos_data_portal_kalawai/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('pos_data_portal_kalawai.listing', {
#             'root': '/pos_data_portal_kalawai/pos_data_portal_kalawai',
#             'objects': http.request.env['pos_data_portal_kalawai.pos_data_portal_kalawai'].search([]),
#         })

#     @http.route('/pos_data_portal_kalawai/pos_data_portal_kalawai/objects/<model("pos_data_portal_kalawai.pos_data_portal_kalawai"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pos_data_portal_kalawai.object', {
#             'object': obj
#         })
