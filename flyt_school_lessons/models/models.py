# -*- coding: utf-8 -*-
import math
import logging

from datetime import datetime, timedelta
from lxml import etree
from psycopg2 import IntegrityError
from werkzeug import urls

from odoo import models, fields, api, tools
from odoo.addons.http_routing.models.ir_http import slug
from openerp.osv.orm import setup_modifiers

_logger = logging.getLogger(__name__)


class ClassLesson(models.Model):
    _name = 'fsl.class_lesson'
    _rec_name = 'lesson_id'

    lesson_group_id = fields.Many2one(
        related='lesson_id.lesson_group_id',
        string="Lesson Group",
    )
    lesson_id = fields.Many2one('survey.survey', string="Lesson")
    class_id = fields.Many2one('fs.class', string="Class")
    scheduled_date = fields.Datetime(help="24-Hour Format", string="Scheduled Date")
    lesson_url = fields.Html(compute='_set_lesson_url', string="Lesson URL")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        result = super(ClassLesson, self).fields_view_get(view_id=view_id,
                                                          view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.fromstring(result['arch'])
        user = self.env.user
        faculty = self.env.ref('openeducat_core.group_op_faculty')

        if view_type == 'form':
            target_field = doc.xpath("//field[@name='lesson_url']")

            if not faculty.id in user.groups_id.ids:
                if target_field:
                    today = (datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
                    field = target_field[0]
                    attrs = "{{'invisible': ['|', ('scheduled_date', '>', '{}'), ('scheduled_date', '=', False)]}}".format(
                        today)
                    field.attrib['attrs'] = attrs
                    setup_modifiers(field, {})

        result['arch'] = etree.tostring(doc)

        return result

    @api.depends('lesson_id')
    def _set_lesson_url(self):
        curr_user = self.env.user

        for r in self:
            html_content = "<a href={}>{}</a>"
            user_input = self.env['survey.user_input'].search([
                ('partner_id', '=', curr_user.partner_id.id),
                ('survey_id', '=', r.lesson_id.id)
            ])
            if user_input:
                lesson_url = user_input.action_view_answers().get('url')
                if user_input.state in ['skip', 'new']:
                    lesson_url = lesson_url.replace('/print/', '/fill/')
                r.lesson_url = html_content.format(lesson_url, r.lesson_id.title)
            else:
                try:
                    r.lesson_url = html_content.format(r.lesson_id.public_url, r.lesson_id.title)
                except Exception as e:
                    r.lesson_url = ""

    _sql_constraints = [
        ('unique_class_lesson',
         'unique(class_id, lesson_id)', 'A class cannot have duplicate lessons'),
    ]


class LessonGroup(models.Model):
    _name = 'fsl.lesson_group'
    _rec_name = 'name'
    _order = 'name,lesson_ids'

    name = fields.Char(string="Name")
    lesson_ids = fields.One2many('survey.survey', 'lesson_group_id', string="Lessons")

    _sql_constraints = [
        ('unique_class_name',
         'unique(name)', 'Name should be unique per class'),
    ]


class UserInputLineEvaluation(models.Model):
    _name = 'fsl.input_line_evaluation'
    _sql_constraints = [
        ('code_uniq_eval_line', 'unique(user_input_evaluation, user_input_line)', 'Questions must be Unique per evaluation!')
    ]

    user_input_evaluation = fields.Many2one(
        'fsl.user_input_evaluation', string='Lesson Evaluation')
    user_input_line = fields.Many2one('survey.user_input_line', string='Answer')
    criteria_evaluations = fields.One2many('fsl.evaluation_criteria', 'input_line_evaluation')

    evaluator_evaluation = fields.Many2one('fs.evaluation', string='Evaluation')
    evaluation_value = fields.Float(compute='_get_evaluation_value')

    # Method to get value of evaluation
    @api.one
    @api.depends('evaluator_evaluation')
    def _get_evaluation_value(self):
        self.evaluation_value = self.evaluator_evaluation.value


class EvaluationCriteria(models.Model):
    _name = 'fsl.evaluation_criteria'

    input_line_evaluation = fields.Many2one('fsl.input_line_evaluation')
    criteria = fields.Many2one('fs.evaluation_criteria')

    evaluator_evaluation = fields.Many2one('fs.evaluation', string='Evaluation')
    evaluation_value = fields.Float(compute='_get_evaluation_value')
    
    # Method to get value of evaluation
    @api.one
    @api.depends('evaluator_evaluation')
    def _get_evaluation_value(self):
        self.evaluation_value = self.evaluator_evaluation.value


class UserInputEvaluation(models.Model):
    _name = 'fsl.user_input_evaluation'
    _rec_name = 'lesson'

    evaluation_url = fields.Char(compute='_get_evaluation_url')
    evaluation_url_html = fields.Html(compute='_get_evaluation_url')
    user_input = fields.Many2one('survey.user_input', string='Lesson')
    evaluator = fields.Many2one('res.partner', string='Evaluator')
    evaluatee = fields.Char(related='user_input.partner_id.display_name', string='Evaluatee')
    lesson = fields.Char(related='user_input.survey_id.title', string='Lesson')
    status = fields.Selection([
        ('evaluated', 'Evaluated'),
        ('draft', 'Draft/To Be Evaluated')
    ], string='Evaluation Status', default='draft')
    quizz_score = fields.Float(related='user_input.quizz_score', string="Score")
    score = fields.Float(string="Total Score", default=float(0))
    remarks = fields.Html(string="Remarks")
    last_displayed_page_id = fields.Many2one('survey.page', string='Last displayed page')

    @api.depends('user_input')
    def _get_evaluation_url(self):
        """
        Creates the url for the answers evaluation
        """
        html_format = "<a class='btn btn-primary' href='%s'>%s</a>"
        base_url = '/' if self.env.context.get(
            'relative_url') else self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for user_input_evaluation in self:
            if user_input_evaluation.status == 'draft':
                url_string = "Evaluate"
            else:
                url_string = "View Evaluation"
            user_input_evaluation.evaluation_url = urls.url_join(
                base_url,
                "lesson/evaluate/%s" % (slug(user_input_evaluation))
            )
            user_input_evaluation.evaluation_url_html = html_format % (
                user_input_evaluation.evaluation_url,
                url_string
            )
    
    @api.model
    def load_eval_line(self, page_id=None):
        UserInputLineEvaluation = self.env['fsl.input_line_evaluation']
        user_eval_line = UserInputLineEvaluation
        UserInputLine = self.env['survey.user_input_line']
        
        user_input = self.user_input
        if page_id:
            user_input_lines = UserInputLine.sudo().search([
                ('user_input_id', '=', user_input.id),
                ('page_id', '=', page_id.id),
                ('page_id.question_ids', '!=', False),
            ])
            user_input_lines = user_input_lines
        else:
            user_input_lines = UserInputLine.sudo().search([('user_input_id', '=', user_input.id)])
        
        self.env.cr.execute("""
            SELECT {eval_id} as user_input_evaluation, uil.id as user_input_line FROM survey_user_input_line uil
            WHERE not exists (SELECT ile.id FROM fsl_input_line_evaluation ile WHERE ile.user_input_line=uil.id AND ile.user_input_evaluation={eval_id})
            AND uil.user_input_id={input_id}""".format(eval_id=self.id, input_id=user_input.id))

        new_eval_lines = self.env.cr.fetchall()

        if new_eval_lines:
            insert_vals =  ",".join(str(ivals) for ivals in new_eval_lines)
            try:
                with self.env.cr.savepoint():
                    self.env.cr.execute("""
                        INSERT INTO fsl_input_line_evaluation (user_input_evaluation, user_input_line) VALUES %s
                    """ % insert_vals)
            except IntegrityError as e:
                _logger.error(e)

        user_eval_line = UserInputLineEvaluation.sudo().search([
            ('user_input_line', 'in', user_input_lines.ids),
            ('user_input_evaluation', '=', self.id)
        ])

        evaluations = self.env['fs.evaluation'].sudo().search([])

        return (
            user_eval_line,
            user_input.sudo().survey_id.lesson_evaluation_type,
            evaluations,
            user_input.token,
        )
    
    @api.model
    def save_eval_line(self, post, button_status):
        # Assume that this block of code is for p2p, p2p+teacher or teacher evaluations only.
        user = self.env.user
        user_input = self.user_input
        eval_criteria = user_input.survey_id.evaluation_criteria
        evaluation_type = user_input.sudo().survey_id.lesson_evaluation_type
        faculty = self.env.ref('openeducat_core.group_op_faculty')

        eval_vals = {}
        lesson_grade = 0.0
        total_evaluation_value = 0.0

        if faculty.id in user.groups_id.ids:
            teacher_score = post.get('score-for-{}'.format(self.id), 0.0)
            remarks = post.get('remarks-for-{}'.format(self.id), "")
            
            eval_vals.update({
                'score': teacher_score,
                'remarks': remarks,
            })
            lesson_grade = float(teacher_score)

        if evaluation_type in ['peer_to_peer', 'peer_to_peer_teacher']:
            Evaluation = self.env['fs.evaluation']
            UserInputLineEvaluation = self.env['fsl.input_line_evaluation']
            EvaluationCriteria = self.env['fsl.evaluation_criteria']

            user_input_line_evaluations = UserInputLineEvaluation.sudo().search(
                [('user_input_evaluation', '=', self.id)])

            criteria_evaluation_value = 0.0
            criteria_average_evaluation_value = 0.0
            total_evaluation_value = 0.0

            evaluations = Evaluation.sudo().search([])
            highest_value = max([e.value for e in evaluations])

            # Saves each evaluaton for each `user_input_line_evaluation`
            # and adds the value of each evaluation to `total_evaluation_value`
            for uile in user_input_line_evaluations:
                for criteria in eval_criteria:
                    criteria_eval_id = EvaluationCriteria.search([('input_line_evaluation', '=', uile.id), ('criteria', '=', criteria.id)])
                    eval_id = post.get("eval_icon_{}_{}".format(uile.id, criteria.id))

                    if criteria_eval_id:
                        criteria_eval_id.sudo().write({
                            'evaluator_evaluation': eval_id
                        })
                    else:
                        criteria_eval_id.sudo().create({
                            'input_line_evaluation': uile.id,
                            'evaluator_evaluation': eval_id,
                            'criteria': criteria.id
                        })

                    criteria_evaluation_value += Evaluation.sudo().search(
                            [('id', '=', eval_id)]).value

                criteria_average_evaluation_value = criteria_evaluation_value / (highest_value * len(eval_criteria))
                total_evaluation_value += criteria_average_evaluation_value
                criteria_evaluation_value = 0.0

            score = total_evaluation_value / len(user_input_line_evaluations)
            
            eval_vals.update({
                'score': score
            })

            # Get all evaluations for the assigned user_input or student answered lesson
            evaluators = self.sudo().search([
                ('user_input', '=', user_input.id),
                ('id', '!=', self.id)
            ])
            if not evaluators.filtered(lambda rec: rec.status == 'draft'):
                # Calculate lesson grade by adding all evaluator score and divided by
                # number of evaluators
                lesson_grade = sum(evaluators.mapped('score')) + score
                lesson_grade = lesson_grade / (len(evaluators) + 1)

        if lesson_grade > 0.0:
            user_input.sudo().write({
                'quizz_score': lesson_grade
            })

        if button_status == 'for_saving':
            # Updates the evaluation status of `user_input_evaluation` to evaluated
            eval_vals.update({'status': 'evaluated'})
        self.sudo().write(eval_vals)
        
        return True

    @api.model
    def calculate_grade(self):
        lesson_types = ['peer_to_peer_teacher', 'peer_to_peer']
        user_inputs = self.env['survey.user_input'].search([
            ('lesson_evaluation_type', 'in', lesson_types)
        ])
        
        for user_input in user_inputs:
            evaluations = env['fsl.user_input_evaluation'].search([('user_input', '=', user_input.id)])
            if evaluations:
                total = 0.0
                total = sum(evaluations.mapped('score'))
                quiz_score = total / len(evaluations)
                user_input.write({'quizz_score': quiz_score})

    @api.model
    def next_page(self, user_input, page_id, go_back=False):
        """ The next page to display to the user, knowing that page_id is the id
            of the last displayed page.

            If page_id == 0, it will always return the first page of the survey.

            If all the pages have been displayed and go_back == False, it will
            return None

            If go_back == True, it will return the *previous* page instead of the
            next page.

            .. note::
                It is assumed here that a careful user will not try to set go_back
                to True if she knows that the page to display is the first one!
                (doing this will probably cause a giant worm to eat her house)
        """
        survey = user_input.survey_id
        pages = list(enumerate(survey.page_ids.filtered(lambda rec: rec.question_ids)))

        # First page
        if page_id == 0:
            return (pages[0][1], 0, len(pages) == 1, len(pages))

        current_page_index = pages.index(next(p for p in pages if p[1].id == page_id))

        # Let's get back, baby!
        if go_back:
            return (pages[current_page_index - 1][1], current_page_index - 1, False, len(pages))
        else:
            # This will show the last page
            if current_page_index == len(pages) - 2:
                return (pages[current_page_index + 1][1], current_page_index + 1, True, len(pages))
            # This will show a regular page
            else:
                return (pages[current_page_index + 1][1], current_page_index + 1, False, len(pages))


class LessonStoryboard(models.Model):
    _name = 'fsl.lesson.storyboard'
    _order = 'sequence asc'

    name = fields.Char(compute="_get_image_url")
    # the image will be generated from this field
    survey_user_line = fields.Many2one('survey.user_input_line')
    story_image = fields.Many2one('ir.attachment', string="Image File")
    sequence = fields.Integer(string="Image Order")

    @api.one
    def _get_image_url(self):
        return u"/web/image/{}".format(self.image.id)


class EvaluationReport(models.Model):
    _name = 'fsl.evaluation_report'
    _auto = False
    _order = 'name'
    
    name = fields.Char(string="Student")
    partner_id = fields.Many2one('res.partner', readonly=True)
    survey_id = fields.Many2one(
        'survey.survey',
        string='Lesson',
        readonly=True,
    )
    quizz_score = fields.Float(string="Score", group_operator='avg', readonly=True)
    state = fields.Char(string="State", readonly=True)
    lesson_evaluation_type = fields.Char(string="Lesson Evaluation Type", readonly=True)

    def _select(self):
        return """
            SELECT
                MIN(sui.id) AS id,
                coalesce(os.last_name, '') ||', ' || coalesce(rp.name, '') || ' ' || coalesce(LEFT(os.middle_name, 1), '') AS name,
                sui.partner_id AS partner_id,
                sui.survey_id AS survey_id,
                sui.quizz_score AS quizz_score,
                sui.state AS state,
                sui.lesson_evaluation_type AS lesson_evaluation_type 
        """

    def _from(self):
        return """
                FROM 
                    survey_user_input sui, op_student os, res_partner rp
                WHERE 
                    sui.partner_id = os.partner_id AND rp.id = os.partner_id
        """

    def _group_by(self):
        return """
            GROUP BY
                sui.id,
                2,
                sui.partner_id,
                sui.survey_id,
                sui.quizz_score
        """

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
            )
        """ % (self._table, self._select(), self._from(), self._group_by())
        )


class JesiSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    terms_and_condition = fields.Html(
        string="Terms and Condition Content"
    )
    default_evaluators_count = fields.Integer(default_model='survey.survey')

    @api.multi
    def apply_to_all_lesson(self):
        # TODO: 
        # Look for a way to update default_evaluators_count when user will not click save button
        # Update all peer to peer lesson
        lessons = self.env['survey.survey'].search([
            ('lesson_evaluation_type', 'not in', ('None', 'system_generated', 'teacher'))
        ])
        lessons.write({
            'evaluators_count': self.default_evaluators_count
        })

    @api.model
    def get_values(self):
        res = super(JesiSettings, self).get_values()
        res.update(
            terms_and_condition=self.env['ir.config_parameter'].sudo().get_param('terms_and_condition')
        )
        return res

    @api.multi
    def set_values(self):
        super(JesiSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('terms_and_condition', self.terms_and_condition)


class OverlayProcessingConfig(models.Model):
    _name = 'fsl.overlay.config'
    _order = 'weekday_from,time_start'

    weekday_list = (
        ('1', 'Monday'),
        ('2', 'Tuesday'),
        ('3', 'Wednesday'),
        ('4', 'Thursday'),
        ('5', 'Friday'),
        ('6', 'Saturday'),
        ('7', 'Sunday'),
    )

    weekday_from = fields.Selection(selection=weekday_list, type='integer')
    weekday_to = fields.Selection(selection=weekday_list, type='integer')
    time_start = fields.Char(help="24hr format, 24:00")
    time_end = fields.Char(help="24hr format, 24:00")
    no_of_batch_to_process = fields.Integer("Video count to process")
    is_from_gt_to = fields.Boolean(compute="check_weekday_range", store=True)

    @api.depends('weekday_from', 'weekday_to')
    def check_weekday_range(self):
        for rec in self:
            rec.is_from_gt_to = rec.weekday_from > rec.weekday_to
