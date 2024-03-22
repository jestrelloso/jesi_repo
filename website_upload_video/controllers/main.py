# -*- coding: utf-8 -*-
# © 2016 ONESTEiN BV (<http://www.onestein.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64

from odoo import http
from odoo.http import request


class WebsiteUploadVideo(http.Controller):
    @http.route('/website_upload_video/attach',
                type='http', auth='user', methods=['POST'], website=True)
    def attach(self, upload=None):
        attachments = request.env['ir.attachment']
        video_data = upload.read()
        attachment_id = attachments.create({
            'name': upload.filename,
            'datas': base64.b64encode(video_data),
            'datas_fname': upload.filename,
            'res_model': 'ir.ui.view',
        })
        return u"""<script type='text/javascript'>
            window.parent['video_upload_callback']({});
        </script>""".format(attachment_id.id) # (attachment_id.id)
