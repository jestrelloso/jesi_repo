from odoo import models, fields, api, tools


class Users(models.Model):
    _inherit = 'res.users'

    terms_and_condition = fields.Boolean(
        string="I have read and agreed on the Terms and Conditions for this site",
        default=False
    )
