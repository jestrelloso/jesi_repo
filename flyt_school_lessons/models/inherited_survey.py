from odoo import models, fields, api


class SurveyPage(models.Model):
    _inherit = 'survey.page'

    shuffle = fields.Boolean(string="Include page to be shuffle", default=True)


class Survey(models.Model):

    _inherit = ['survey.survey']
    _order = 'lesson_group_id,title'

    # Defaults `quizz_mode` to true
    quizz_mode = fields.Boolean(string='Quiz Mode', default=True)

    # Added field `evaluation_type` to handle different type of evaluation options
    lesson_evaluation_type = fields.Selection([
        ('None', 'None'),
        ('system_generated', 'System Generated Assessment'),
        ('peer_to_peer', 'Peer-to-peer Assessment'),
        # ('peer_to_peer_system', 'Peer-to-peer + System Generated Assessment'),
        ('teacher', 'Teacher Evaluation'),
        ('peer_to_peer_teacher', 'Peer-to-peer + Teacher Evaluation')
    ], string='Lesson Evaluation Type', default='peer_to_peer_teacher', required=True)

    subject_id = fields.Many2one('op.subject', 'Subject')
    college_id = fields.Many2one('fs.college', 'College')
    kpi = fields.Html(string="KPI Information")
    lesson_group_id = fields.Many2one('fsl.lesson_group', String="Lesson Group")
    evaluation_criteria = fields.Many2many('fs.evaluation_criteria')
    evaluators_count = fields.Integer(string="Evaluators Count", required=False, default=0)

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
        pages = list(enumerate(user_input.user_input_pages.mapped('page_id')))

        # First page
        if page_id == 0:
            return (pages[0][1], 0, len(pages) == 1)

        current_page_index = pages.index(next(p for p in pages if p[1].id == page_id))

        # All the pages have been displayed
        if current_page_index == len(pages) - 1 and not go_back:
            return (None, -1, False)
        # Let's get back, baby!
        elif go_back and survey.users_can_go_back:
            return (pages[current_page_index - 1][1], current_page_index - 1, False)
        else:
            # This will show the last page
            if current_page_index == len(pages) - 2:
                return (pages[current_page_index + 1][1], current_page_index + 1, True)
            # This will show a regular page
            else:
                return (pages[current_page_index + 1][1], current_page_index + 1, False)
    
    @api.multi
    def _compute_survey_statistic(self):
        UserInput = self.env['survey.user_input']

        sent_survey = UserInput.search([('survey_id', 'in', self.ids), ('type', '=', 'link')])
        start_survey = UserInput.search(['&', ('survey_id', 'in', self.ids), '|', ('state', '=', 'skip'), ('state', '=', 'done')])
        complete_survey = UserInput.search([('survey_id', 'in', self.ids), ('state', '=', 'done')])

        for survey in self:
            survey.tot_sent_survey = len(sent_survey.filtered(lambda user_input: user_input.survey_id == survey))
            survey.tot_start_survey = len(start_survey.filtered(lambda user_input: user_input.survey_id == survey and user_input.partner_id))
            survey.tot_comp_survey = len(complete_survey.filtered(lambda user_input: user_input.survey_id == survey))

    @api.onchange('lesson_evaluation_type')
    def _onchange_lesson_evaluation_type(self):
        self.quizz_mode = True if self.lesson_evaluation_type == 'system_generated' else False

    @api.depends('title, subject_id')
    def name_get(self):
        result = []
        for rec in self:
            if rec.subject_id:
                name = "{} / {}".format(rec.subject_id.name, rec.title)
            else:
                name = rec.title
            result.append((rec.id, name))
        # sorted_result = sorted(result, key=lambda tup: (tup[1]))
        return result
