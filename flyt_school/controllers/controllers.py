# -*- coding: utf-8 -*-
from odoo import http

# class FlytSchool(http.Controller):
#     @http.route('/flyt_school/flyt_school/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/flyt_school/flyt_school/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('flyt_school.listing', {
#             'root': '/flyt_school/flyt_school',
#             'objects': http.request.env['flyt_school.flyt_school'].search([]),
#         })

#     @http.route('/flyt_school/flyt_school/objects/<model("flyt_school.flyt_school"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('flyt_school.object', {
#             'object': obj
#         })