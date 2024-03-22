# -*- coding: utf-8 -*-

from odoo import models, api
from openerp.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = ['res.partner']

    @api.multi
    def write(self, vals):
        for rec in self:
            admin_user = self.env['res.users'].search([('id', '=', 1)])
            if rec.id == admin_user.partner_id.id and self._uid != 1:
                raise ValidationError("You are not allowed to edit this record")
            super(ResPartner, rec).write(vals)
        return True
