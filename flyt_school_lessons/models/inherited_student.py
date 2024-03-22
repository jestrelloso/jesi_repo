# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Student(models.Model):
    _inherit = ['op.student']

    eval_count = fields.Integer(compute='_eval_count', string="Number of Evaluations")
    to_evaluate_count = fields.Integer(
        compute='_to_evaluate_count', string="Number of Lessons to Evaluate")
    aboutme_video_id = fields.Integer('About me Video')

    def _to_evaluate_count(self):
        self.to_evaluate_count = self.env['fsl.user_input_evaluation'].search_count([
            ('evaluator', '=', self.partner_id.id),
            ('status', '=', 'draft')
        ])

    def _eval_count(self):
        self.eval_count = self.env["survey.user_input"].search_count([
            ('state', '=', 'done'),
            ('partner_id', '=', self.partner_id.id),
            ('lesson_evaluation_type', '!=', 'None'),
        ])

    def student_evaluations(self):
        treeview_id = self.env.ref('flyt_school_lessons.view_survey_user_input_tree').id
        action_data = {
            "type": "ir.actions.act_window",
            "name": "Evaluations",
            "view_mode": "tree",
            "view_id": treeview_id,
            "res_model": "survey.user_input",
            "help": "No evaluations yet.",
            "domain": [
                ('state', '=', 'done'),
                ('partner_id', '=', self.partner_id.id),
                ('lesson_evaluation_type', '!=', 'None'),
            ],
            "context": {
                'group_by': ['subject_id']
            }
        }
        return action_data

    @api.multi
    def lessons_to_evaluate(self):
        lesson_evaluate_action = self.env.ref('flyt_school_lessons.act_open_evaluations_student_view')
        action_data = lesson_evaluate_action.read()[0]
        action_data.update({
            'domain': [
                ('evaluator', '=', self.partner_id.id),
                ('status', '=', 'draft'),
            ]
        })
        return action_data
