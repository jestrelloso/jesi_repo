# -*- coding: utf-8 -*-

from odoo import models, api


class WizardOpStudent(models.TransientModel):
    _inherit = 'wizard.op.student'

    @api.multi
    def create_student_user(self):
        """
        The user groups to be included when creating a new user
        are based on the default student (Sumita) demo account's user groups
        """
        user_group_student = self.env.ref('openeducat_core.group_op_student')
        user_group_employee = self.env.ref('base.group_user')
        user_group_technical_features = self.env.ref('base.group_no_one')
        active_ids = self.env.context.get('active_ids', []) or []
        records = self.env['op.student'].browse(active_ids)
        self.env['res.users'].create_user(
            records,
            [user_group_student.id, user_group_employee.id, user_group_technical_features.id]
        )
