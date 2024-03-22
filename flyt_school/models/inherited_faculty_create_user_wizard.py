# -*- coding: utf-8 -*-

from odoo import models, api


class WizardOpStudent(models.TransientModel):
    _inherit = 'wizard.op.faculty'

    @api.multi
    def create_faculty_user(self):
        """
        The user groups to be included when creating a new user
        are based on the default faculty (Sumita) demo account's user groups
        """
        user_group_faculty = self.env.ref('openeducat_core.group_op_faculty')
        user_group_employee = self.env.ref('base.group_user')
        user_group_technical_features = self.env.ref('base.group_no_one')
        active_ids = self.env.context.get('active_ids', []) or []
        records = self.env['op.faculty'].browse(active_ids)
        self.env['res.users'].create_user(
            records,
            [user_group_faculty.id, user_group_employee.id, user_group_technical_features.id]
        )
