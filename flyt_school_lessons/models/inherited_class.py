# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import math
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError


class Class(models.Model):
    _inherit = ['fs.class']

    semester_id = fields.Many2one()
    subject_id = fields.Many2one(required=True)
    class_lesson_ids = fields.One2many(
        'fsl.class_lesson',
        'class_id',
        string="Lessons",
    )
    to_evaluate_count = fields.Integer(
        compute='_to_evaluate_count', string="Number of Lessons to Evaluate")

    def _to_evaluate_count(self):
        lesson_ids = self.class_lesson_ids.mapped('lesson_id').ids
        self.to_evaluate_count = self.env['fsl.user_input_evaluation'].search_count([
            ('evaluator', '=', self.faculty_id.partner_id.id),
            ('user_input.survey_id', 'in', lesson_ids),
            ('status', '=', 'draft')
        ])

    @api.multi
    def lessons_to_evaluate(self):
        lesson_evaluate_action = self.env.ref('flyt_school_lessons.act_open_evaluations_student_view')
        lesson_ids = self.class_lesson_ids.mapped('lesson_id').ids
        action_data = lesson_evaluate_action.read()[0]
        action_data.update({
            'domain': [
                ('evaluator', '=', self.faculty_id.partner_id.id),
                ('user_input.survey_id', 'in', lesson_ids),
                ('status', '=', 'draft')
            ]
        })
        return action_data

    def unevaluated_lessons(self):
        user = self.env.user
        faculty = self.env.ref('openeducat_core.group_op_faculty')
        treeview_id = self.env.ref('flyt_school_lessons.view_survey_user_input_tree_no_eval').id

        if not faculty.id in user.groups_id.ids:
            partner_id = [user.partner_id.id]
        else:
            partner_id = self.student_ids.mapped('partner_id').ids
        action_data = {
            "type": "ir.actions.act_window",
            "name": "No Evaluations",
            "view_mode": "tree",
            "view_id": treeview_id,
            "res_model": "survey.user_input",
            "help": "No evaluations yet.",
            "domain": [
                ('state', '=', 'done'),
                ('subject_id', '=', self.subject_id.id),
                ('partner_id', 'in', partner_id),
                ('lesson_evaluation_type', '=', 'None'),
            ],
            "context": {
                'group_by': ['partner_id']
            }
        }
        return action_data

    def student_evaluations(self):
        user = self.env.user
        faculty = self.env.ref('openeducat_core.group_op_faculty')
        treeview_id = self.env.ref('flyt_school_lessons.view_survey_user_input_tree').id

        if not faculty.id in user.groups_id.ids:
            partner_id = [user.partner_id.id]
        else:
            partner_id = self.student_ids.mapped('partner_id').ids
        action_data = {
            "type": "ir.actions.act_window",
            "name": "Evaluations",
            "view_mode": "tree",
            "view_id": treeview_id,
            "res_model": "survey.user_input",
            "help": "No evaluations yet.",
            "domain": [
                ('state', '=', 'done'),
                ('subject_id', '=', self.subject_id.id),
                ('partner_id', 'in', partner_id),
                ('lesson_evaluation_type', '!=', 'None'),
            ],
            "context": {
                'group_by': ['partner_id']
            }
        }
        return action_data

    def evaluations_report(self):
        pivot_view_id = self.env.ref('flyt_school_lessons.view_evaluation_report_pivot').id

        action_data = {
            "type": "ir.actions.act_window",
            "name": "Evaluation Report",
            "view_mode": "pivot",
            "view_id": pivot_view_id,
            "res_model": "fsl.evaluation_report",
            "help": "No evaluation report yet.",
            "domain": [
                ('state', '=', 'done'),
                ('partner_id', 'in', self.student_ids.mapped('partner_id').ids),
                ('lesson_evaluation_type', '!=', 'None')
            ],
        }
        return action_data

    def generate_class_lessons(self):
        self.ensure_one()
        if self.subject_id and self.department_id and self.start_time:
            subject_lessons = self.subject_id.lessons.filtered(lambda lesson: lesson.college_id == self.department_id.college_id)
            
            # delete all class lessons with lessons not part in the selected subject's lessons
            self.class_lesson_ids.filtered(lambda rec: rec.lesson_id not in subject_lessons).unlink()
            class_lesson_obj = self.env['fsl.class_lesson']
            start_time = self.start_time
            minutes, hours = math.modf(start_time)
            hours = int(hours)
            minutes = math.floor(minutes * 60)
            scheduled_date = datetime.now().replace(hour=hours, minute=minutes, second=0) - timedelta(hours=8)

            # create new class lesson with lessons not yet existing 
            for lesson in subject_lessons.filtered(lambda rec: rec not in self.class_lesson_ids.mapped('lesson_id')):
                self.class_lesson_ids |= class_lesson_obj.create({
                    'lesson_id': lesson.id,
                    'scheduled_date': scheduled_date
                })

    @api.onchange('subject_id')
    def onchange_subject_id(self):
        self.department_id = False
        college_ids = self.subject_id.lessons.mapped('college_id').ids 
        return {
            'domain': {
                'department_id': [('college_id', 'in', college_ids)],
            }
        }

    @api.onchange('department_id')
    def onchange_department_id(self):
        return {
            'domain': {
                'section_id':[('department_id', '=', self.department_id.id)],
            }
        }

    @api.constrains('start_time', 'end_time')
    def _check_time_format(self):
        if self.filtered(lambda rec: rec.start_time >= 24 or rec.end_time >= 24):
            raise ValidationError(_("Time cannot exceed to 24:00 or higher. It's only from 00:00 to 23:59"))
