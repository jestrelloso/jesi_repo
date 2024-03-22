import functools
import werkzeug

import odoo
import odoo.addons.web.controllers.main as web_controller

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.modules import get_resource_path


class HomeExtension(web_controller.Home):

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        web_controller.ensure_db()

        if not request.session.uid:
            return werkzeug.utils.redirect('/web/login', 303)

        curr_user_rec = request.env['res.users'].sudo().browse([request.session.uid])
        if not curr_user_rec.terms_and_condition and curr_user_rec.id != 1:
            return werkzeug.utils.redirect('/web/terms_and_condition', 303)

        if kw.get('redirect'):
            return werkzeug.utils.redirect(kw.get('redirect'), 303)

        request.uid = request.session.uid
        try:
            context = request.env['ir.http'].webclient_rendering_context()
            response = request.render('web.webclient_bootstrap', qcontext=context)
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        except AccessError:
            return werkzeug.utils.redirect('/web/login?error=access')

    @http.route('/web/terms_and_condition', type='http', auth='user')
    def web_terms_and_condition(self, redirect=None, **kwargs):
        if request.httprequest.method == 'POST' and request.session.uid:
            request.env['res.users'].browse([request.session.uid]).sudo().write({'terms_and_condition': True})
            return http.redirect_with_hash('/web')
        
        context_data = {
            'terms_and_condition': request.env['ir.config_parameter'].sudo().get_param('terms_and_condition')
        }
        return request.render('flyt_school_lessons.terms_and_condition', context_data)


class BinaryExtension(web_controller.Binary):
    """
    Overriding of `content_image` method in the WebsiteSurvey Controller
    Controller https://github.com/odoo/odoo/blob/11.0/addons/web/controllers/main.py
    """

    def attach_extra_headers(self, response):
        mimetype = response.headers.get('Content-Type')
        if mimetype and mimetype.split('/')[0] and mimetype.split('/')[0] in ['audio', 'video']:
            response.headers.add('Connection', 'keep-alive')
            response.headers.add('Accept-Ranges', 'bytes')
        return response

    @http.route()
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                      filename_field='datas_fname', unique=None, filename=None, mimetype=None,
                      download=None, width=0, height=0, crop=False, access_token=None):
        id = isinstance(id, str) and id.replace(',', '') or id  # remove comma if id is string
        content_image_response = super(BinaryExtension, self).content_image(xmlid, model, id, field,
                      filename_field, unique, filename, mimetype, download, width, height,
                      crop, access_token)
        content_image_response = self.attach_extra_headers(content_image_response)
        return content_image_response

    @http.route()
    def content_common(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       filename=None, filename_field='datas_fname', unique=None, mimetype=None,
                       download=None, data=None, token=None, access_token=None, **kw):
        
        content_common_response = super(BinaryExtension, self).content_common(xmlid, model, id, field,
                       filename, filename_field, unique, mimetype, download, data,
                       token, access_token, **kw)
        content_common_response = self.attach_extra_headers(content_common_response)
        return content_common_response

    # Overriding controller for default company logo.
    # ref: https://stackoverflow.com/questions/38569537/how-to-change-the-default-logo-through-module-in-odoo-9?rq=1
    @http.route()
    def company_logo(self, dbname=None, **kw):
        imgname = 'logo'
        imgext = '.png'
        placeholder = functools.partial(get_resource_path, 'flyt_school_lessons', 'static', 'src', 'img')
        # uid = None
        # if request.session.db:
        #     dbname = request.session.db
        #     uid = request.session.uid
        # elif dbname is None:
        #     dbname = db_monodb()

        # if not uid:
        #     uid = odoo.SUPERUSER_ID
        
        response = http.send_file(placeholder(imgname + imgext))
        

        # if not dbname:
        #     response = http.send_file(placeholder(imgname + imgext))
        # else:
        #     try:
        #         # create an empty registry
        #         registry = odoo.modules.registry.Registry(dbname)
        #         with registry.cursor() as cr:
        #             company = int(kw['company']) if kw and kw.get('company') else False
        #             if company:
        #                 cr.execute("""SELECT logo_web, write_date
        #                                 FROM res_company
        #                                WHERE id = %s
        #                            """, (company,))
        #             else:
        #                 cr.execute("""SELECT c.logo_web, c.write_date
        #                                 FROM res_users u
        #                            LEFT JOIN res_company c
        #                                   ON c.id = u.company_id
        #                                WHERE u.id = %s
        #                            """, (uid,))
        #             row = cr.fetchone()
        #             if row and row[0]:
        #                 image_base64 = base64.b64decode(row[0])
        #                 image_data = io.BytesIO(image_base64)
        #                 imgext = '.' + (imghdr.what(None, h=image_base64) or 'png')
        #                 response = http.send_file(image_data, filename=imgname + imgext, mtime=row[1])
        #             else:
        #                 response = http.send_file(placeholder('nologo.png'))
        #     except Exception:
        #         response = http.send_file(placeholder(imgname + imgext))

        return response
        
    @http.route([
        '/web/binary/support_logo',
    ], type='http', auth="none", cors="*")
    def support_logo(self, dbname=None, **kw):
        imgname = 'logo-back'
        imgext = '.png'
        placeholder = functools.partial(get_resource_path, 'flyt_school_lessons', 'static', 'src', 'img')
        response = http.send_file(placeholder(imgname + imgext))
        return response
