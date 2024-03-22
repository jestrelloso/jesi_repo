from odoo import api, fields, models


class SurveyUserInputPages(models.Model):
    _name = "survey.user_input_pages"
    _order = "sequence,page_id"

    survey_user_input_id = fields.Many2one(
        comodel_name="survey.user_input"
    )
    page_id = fields.Many2one(
        comodel_name="survey.page"
    )
    sequence = fields.Integer('Page Number')
