# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Subject(models.Model):
    _inherit = ['op.subject']

    description = fields.Text()
    lessons = fields.One2many(
        comodel_name = 'survey.survey',
        inverse_name = 'subject_id',
        string = 'Lessons'
    )
    class_count = fields.Integer(compute='_class_count', string="Number of Classes")

    @api.multi
    def _class_count(self):
        self.class_count = len(self.env["fs.class"].search(
            [("subject_id", "=", self.id)]))
