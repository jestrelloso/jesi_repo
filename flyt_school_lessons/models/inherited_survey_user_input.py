import random

from datetime import datetime
from lxml import etree
from werkzeug import urls

from odoo.addons.http_routing.models.ir_http import slug
from odoo import models, fields, api
from odoo.osv.orm import setup_modifiers



class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'
    _sql_constraints = [
        ('uniq_inputs', 'unique(survey_id, partner_id)','Only 1 attempt is allowed per lesson')
    ]

    evaluation_result_url = fields.Char(compute='_get_evaluation_results_url')
    evaluation_result_url_html = fields.Html(compute='_get_evaluation_results_url')
    lesson_group_id = fields.Many2one(
        related="survey_id.lesson_group_id",
        string="Lesson Group",
        readonly=True,
        store=True
    )
    college_id = fields.Many2one(
        related="survey_id.college_id",
        string="College",
        readonly=True,
        store=True
    )
    department_id = fields.Many2one(
        "fs.department",
        compute="_get_student_info",
        string="Department",
        readonly=True,
        store=True
    )
    section_id = fields.Many2one(
        "fs.section",
        compute="_get_student_info",
        string="Section",
        readonly=True,
        store=True
    )
    subject_and_faculty = fields.Char(
        compute="_get_student_info",
        string="Subject and Faculty",
        readonly=True,
        store=True
    )
    time_start = fields.Datetime('Time Start', readonly=True)
    time_end = fields.Datetime('Time End', readonly=True)
    duration = fields.Char('Duration', compute='_get_duration')
    subject_id = fields.Many2one(
        related="survey_id.subject_id",
        string="Subject",
        readonly=True,
        store=True
    )
    # Added store=True to this existing
    quizz_score = fields.Float(
        "Score",
        compute="_compute_quizz_score",
        default=0.0,
        store=True,
        group_operator='avg'
    )
    lesson_evaluation_type = fields.Selection(
        related='survey_id.lesson_evaluation_type', store=True)
    user_input_pages = fields.One2many(
        comodel_name="survey.user_input_pages",
        inverse_name="survey_user_input_id"
    )
    user_input_evaluation_ids = fields.One2many(
        comodel_name="fsl.user_input_evaluation",
        inverse_name="user_input"
    )

    @api.model
    def _apply_ir_rules(self, query, mode='read'):
        # This is to override ir rule condition to include checking user evaluation model if 
        # current user is an evaluator to allow read to the current survey_user_input record.
        if self.env.user.id != 1 and mode == 'read':
            evaluator_ids = self.sudo().mapped('user_input_evaluation_ids.evaluator')
            if evaluator_ids:
                if self.env.user.partner_id.id in evaluator_ids.ids:
                    return
        return super(SurveyUserInput, self)._apply_ir_rules(query=query, mode=mode)

    @api.model
    def create(self, vals):
        user_input_id = super(SurveyUserInput, self).create(vals)

        if user_input_id:
            user_pages = []
            sequence = []
            not_shuffle_page = self.env['survey.page']
            page_ids = user_input_id.survey_id.page_ids
            #TODO: Handle scenario where pages have same sequence number
            shuffle_seq = page_ids.mapped('sequence')
            page_ids_length = len(page_ids)

            shuffle_seq = [seq for seq in range(page_ids_length)]

            # Check if the pages has shuffle turned off
            if page_ids.filtered(lambda rec: rec.shuffle == False):
                for ind, rec in enumerate(page_ids):
                    # if page is not to be shuffled automatically append it to user_pages,
                    # add the page record to not_shuffle page variable and remove the sequence
                    # number from the shuffle_seq list to avoid duplicate
                    if not rec.shuffle:
                        if ind in shuffle_seq:
                            shuffle_seq.remove(ind)
                        not_shuffle_page += rec
                        user_pages.append(
                            (0, 0, {'page_id': rec.id, 'sequence': ind})
                        )
            
            # Actual process for shuffling pages, if all pages shuffle is equal False this loop
            # Will not run due to page_ids will be blank
            for page in page_ids:
                # shuffle sequences
                random.shuffle(shuffle_seq)
                user_pages.append(
                    (0, 0, {
                        'page_id': page.id,
                        'sequence': shuffle_seq.pop() if shuffle_seq else page.sequence
                    })
                )
            user_input_id.sudo().write({'user_input_pages': user_pages})
        return user_input_id

    # Updated computation from sum only to (sum / 2) + 50
    def _compute_quizz_score(self):
        for user_input in self:
            user_input.quizz_score = 15.0
            if user_input.user_input_line_ids:
                if user_input.survey_id.lesson_evaluation_type == 'system_generated':
                    total_score = sum(user_input.user_input_line_ids.mapped(
                        'question_id').mapped('labels_ids').mapped('quizz_mark'))
                    raw_score = sum(user_input.user_input_line_ids.mapped('quizz_mark'))

                    if total_score != 0.0:
                        user_input.quizz_score = round((((raw_score / total_score) * 85) + 15), 1)
                else:
                    user_input.quizz_score = sum(user_input.user_input_line_ids.mapped('quizz_mark'))

    @api.depends('state')
    def _get_evaluation_results_url(self):
        """
        Creates the url for the evaluation results, only after the `state` of the `user_input` is set to 'done'
        """
        base_url = '/' if self.env.context.get(
            'relative_url') else self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        html_format = "<a class='btn btn-primary' href='{}'>{}</a>"
        url_string = "View Evaluation Result"
        
        for user_input in self:
            if user_input.state == 'done':
                if user_input.survey_id.lesson_evaluation_type != 'system_generated':
                    user_input.evaluation_result_url = urls.url_join(
                        base_url,
                        "evaluation/%s/result" % (slug(user_input))
                    )
                    user_input.evaluation_result_url_html = html_format.format(
                        user_input.evaluation_result_url,
                        url_string
                    )
                else:
                    user_input.evaluation_result_url = "{}/{}".format(
                        user_input.survey_id.print_url,
                        user_input.token
                    )
                    user_input.evaluation_result_url_html = html_format.format(
                        user_input.evaluation_result_url,
                        url_string
                    )

    @api.depends("time_start", "time_end")
    def _get_duration(self):
        for record in self:
            start = datetime.strptime(record.time_start, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(record.time_end, "%Y-%m-%d %H:%M:%S")
            duration = end - start
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            int_hours = int(hours)
            int_minutes = int(minutes)
            int_seconds = int(seconds)

            if int_hours != 0 and int_minutes != 0:
                record.duration = "{} Hour(s) {} Minute(s) and {} Seconds".format(
                    int_hours, int_minutes, int_seconds)
            if int_hours == 0 and int_minutes != 0:
                record.duration = "{} Minute(s) and {} Seconds".format(int_minutes, int_seconds)
            if int_hours == 0 and int_minutes == 0:
                record.duration = "{} Seconds".format(int_seconds)

    @api.depends("partner_id")
    def _get_student_info(self):
        for record in self:
            student_obj = self.env['op.student'].search(
                [('partner_id', '=', record.partner_id.id)]
            )
            record.department_id = student_obj.department_id
            record.section_id = student_obj.section_id

            class_obj = self.env["fs.class"].search([
                ('subject_id', '=', record.subject_id.id),
                ('student_ids', 'in', student_obj.id)
            ])
            record.subject_and_faculty = "{} / {} {}".format(
                record.subject_id.name,
                class_obj.faculty_id.name,
                class_obj.faculty_id.last_name
            )
