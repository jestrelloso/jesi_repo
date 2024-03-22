# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Faculty(models.Model):
    _inherit = ['op.faculty']

    class_ids = fields.One2many('fs.class', 'faculty_id', string="Classes")
    class_count = fields.Integer(compute='_class_count', string="Number of Classes")
    account_id = fields.Char('Faculty ID', required=True)
    ext_name = fields.Char('Ext')
    # Overwrite the nationality field from openeducat.core, change selection into char field.
    nationality = fields.Char(string="Nationality")
    subject_faculty_ids = fields.Many2many(
        'op.subject',
        compute='_faculty_subjects',
        readonly=True
    )

    def _class_count(self):
        self.class_count = self.env["fs.class"].search_count([
            ("faculty_id", "=", self.id)
        ])

    def _faculty_subjects(self):
        self.subject_faculty_ids = self.env["fs.class"].search([
            ("faculty_id", "=", self.id)
        ]).mapped('subject_id')

    @api.model
    def create(self, vals):
        faculty = super(Faculty, self).create(vals)
        # Create a user account for faculty with access rights
        user_group_faculty = self.env.ref('openeducat_core.group_op_faculty')
        user_group_employee = self.env.ref('base.group_user')
        user_group_technical_features = self.env.ref('base.group_no_one')
        self.env['res.users'].create_user(
            faculty,
            [user_group_faculty.id, user_group_employee.id, user_group_technical_features.id]
        )
        return faculty
