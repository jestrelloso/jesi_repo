import re
import uuid
from collections import OrderedDict

from odoo import models, fields, api
from openerp.exceptions import ValidationError


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    # Added field `question_type` to handle different type of survey questions
    question_type = fields.Selection([
        ('text_only', 'Text only'),
        ('text_single_image_content', 'Text with single image'),
        ('text_audio_content', 'Text with audio content'),
        ('text_video_content', 'Text with video content')
    ], string='Question Type', default='text_only', required=True)
    # Changed string for `type` "Type of Question", added three new answer types
    type = fields.Selection(string='Answer Type', selection_add=[
        ('audio_input', 'Audio Input (audio recording)'),
        ('video_input', 'Video Input (video recording)'),
        ('storyboard_type', 'Storyboard Type')
    ])
    # Adding a field for a file to be used for image, audio or video
    # Using a single file upload for now
    image_file = fields.Binary(
        string='Image', help='This is the image to be displayed in the question.')
    video_file = fields.Binary(
        string='Video', help='This is the video to be displayed in the question.')
    audio_file = fields.Binary(
        string='Audio', help='This is the audio to be displayed in the question.')
    attached_media_file = fields.Many2one('ir.attachment', string="Attached Video/Audio question")
    add_to_profile = fields.Boolean('Send response to Student profile')
    recording_answer_time_limit = fields.Integer(
        string='Answer Recording Time Limit (minutes)',
        help='Set the time recording limit for the audio/video answer.',
        default=0
    )
    student_fields = fields.Selection(
        '_get_student_field_choices',
        'Profile Data',
    )
    selection_values_html = fields.Html(
        compute="_get_html_selection_preview",
    )
    enable_html_field = fields.Boolean(default=True, string='Enable HTML Field')
    word_count = fields.Integer(string='Minimum Number of Words')
    is_reaction_video = fields.Boolean(string='Is Reaction Video', default=False)
    story_images = fields.One2many('ir.attachment', compute="get_compute_images")

    @api.model
    def create(self, vals):
        if vals.get('video_file', False) or vals.get('audio_file', False):
            vals = self._attach_media_file(False, vals)

        return super(SurveyQuestion, self).create(vals)

    @api.multi
    def write(self, vals):
        for rec in self:
            if vals.get('video_file', False) or vals.get('audio_file', False):
                vals = rec._attach_media_file(rec.id, vals)
            super(SurveyQuestion, rec).write(vals)

        return True

    @api.onchange('type')
    def onchange_answer_type(self):
        if self.type == 'storyboard_type':
            self.question_type = 'text_only'

    @api.multi
    def open_attachment_wizard(self):
        action_data = {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ir.attachment',
            'context': {
                'default_res_model': 'survey.question',
                'default_res_id': self.id,
            },
            'target':'new'
        }
        return action_data
    
    @api.one
    @api.model
    def get_compute_images(self):
        self.story_images = self.env['ir.attachment'].search([
            '|',
            ('mimetype', '=', 'image/jpeg'),
            ('mimetype', '=', 'image/png'),
            ('res_model', '=', 'survey.question'),
            ('res_id', '=', self.id),
        ])

    @api.onchange('recording_answer_time_limit')
    def _check_time_limit(self):
        for record in self:
            if record.recording_answer_time_limit < 0:
                raise ValidationError("Negative recording time values are not allowed.")

    @api.depends('video_file')
    def _decode_video_file(self):
        for record in self:
            if record.video_file:
                record.decoded_video_file = record.video_file.decode("utf-8")

    @api.depends('audio_file')
    def _decode_audio_file(self):
        for record in self:
            if record.audio_file:
                record.decoded_audio_file = record.audio_file.decode("utf-8")

    def _attach_media_file(self, question_id, vals):
        """
        `question_id`: browse id from database for updated object,
        `vals`: get if there is video file or audio file to be saved as attachment
        """
        Attachments = self.env['ir.attachment']
        question_id = self.browse(question_id)
        if question_id.attached_media_file:
            question_id.attached_media_file.write({
                'datas': vals.get('video_file', vals.get('audio_file', False))
            })
            vals['attached_media_file'] = question_id.attached_media_file.id
        else:
            unique_filename = str(uuid.uuid1())
            attached_media = Attachments.create({
                'name': unique_filename,
                'mimetype': 'video/webm' if 'video_file' in vals else 'audio/webm',
                'datas': vals.get('video_file', vals.get('audio_file', False)),
                'datas_fname': unique_filename
            })
            vals['attached_media_file'] = attached_media.id

        return vals

    def cron_data(self):
        Attachments = self.env['ir.attachment']
        media_files = self.search([('question_type', 'in', ['text_audio_content', 'text_video_content'])])
        for rec in media_files:
            unique_filename = str(uuid.uuid1())
            print("record id: {} | unique_filename: {}".format(rec.id, unique_filename))
            media_vals = {
                'name': unique_filename,
                'datas_fname': unique_filename,
            }
            if rec.question_type == 'text_audio_content':
                media_vals.update({
                    'mimetype': 'audio/webm',
                    'datas': rec.audio_file
                })
            else:
                media_vals.update({
                    'mimetype': 'video/webm',
                    'datas': rec.video_file
                })
            attached_media = Attachments.create(media_vals)
            rec.write({'attached_media_file': attached_media.id})

    def _get_student_field_choices(self):
        choices = []
        # The keys is based on survey.question type selection field
        # the value represents the field type it needs to be associated with

        # Note: a fields.Monetary exists, this is used for fields that uses currency.
        # For selection type assumed that user knows what he or she is doing
        student_obj = self.env['op.student']
        student_fields_keys = OrderedDict(sorted(student_obj._fields.items())).keys()

        for name in student_fields_keys:
            if name != 'id':
                field = student_obj._fields[name]

                if field.type in ['text', 'char', 'integer', 'date', 'selection', 'html']:
                    if name == 'name':
                        choices.append((name, 'First Name'))
                    elif field.store:
                        choices.append((name, field.string))
        return sorted(choices, key=lambda x: x[1])

    @api.onchange('student_fields', 'type')
    def _get_html_selection_preview(self):
        # How to handle multiple choice
        answer_type_mapping = {
            'free_text': ['text', 'char', 'html'],
            'textbox': ['text', 'char', 'selection'],
            'simple_choice': ['text', 'char'],
            'numerical_box': ['integer'],
            'date': ['date'],
            'video_input': ['integer']
        }
        student_obj = self.env['op.student']
        allowable_type = []
        
        self.selection_values_html = "Info if profile data selected is a selection field"

        if self.add_to_profile:
            if self.student_fields:
                student_field = student_obj._fields[self.student_fields]

                if student_field.type == 'selection':
                    field_values = student_field.selection

                    # Check if choices are assigned in a function
                    if callable(field_values):
                        field_values = field_values(student_obj)

                    html_content = "<ul>"
                    for key, value in field_values:
                        html_content += "<li>{} = {}</li>".format(key, value)

                    self.selection_values_html = "{}</ul>".format(html_content)

                allowable_type = answer_type_mapping.get(self.type)

                warning_obj = {
                    'warning': {
                        'title': 'Warning!',
                        'message': 'Selected field type is not the same type for answer',
                    }
                }

                if allowable_type:
                    if student_field.type not in allowable_type:
                        return warning_obj

                    if self.type != 'video_input' and student_field.name == 'aboutme_video_id':
                        return warning_obj
                else:
                    return warning_obj

    @api.multi
    def validate_free_text(self, post, answer_tag):
        self.ensure_one()
        errors = {}
        answer = post[answer_tag].strip()
        cleaner = re.compile('<.*?>')
        cleaned_answer = cleaner.sub(' ', answer)
        answer_length = len(cleaned_answer.replace('&nbsp;', '').split())
        # Empty answer to mandatory question
        if self.constr_mandatory and not answer_length != 0:
            errors.update({answer_tag: self.constr_error_msg})
        # If answer length is less than word count
        if answer_length != 0 and answer_length < self.word_count:
            errors.update({answer_tag: "Answer must have at least {} words. Yours only has {}.".format(
                self.word_count, answer_length)})

        return errors

    @api.model
    def _validate_audio_video_input(self, post, answer_tag):
        errors = {}
        if self.constr_mandatory and not post.get(answer_tag) == 'Done Recording':
                errors.update({answer_tag: self.constr_error_msg})

        return errors
    
    @api.multi
    def validate_audio_input(self, post, answer_tag):
        self.ensure_one()
        return self._validate_audio_video_input(post, answer_tag)

    @api.multi
    def validate_video_input(self, post, answer_tag):
        self.ensure_one()
        return self._validate_audio_video_input(post, answer_tag)

    @api.one
    def get_attached_media_recording(self, token):
        # Get only the latest user_input_line, if user answered multiple times
        uil = self.env['survey.user_input_line'].search([
            ('user_input_id.token', '=', token),
            ('question_id', '=', self.id),
            ('page_id', '=', self.page_id.id),
        ], limit=1, order="create_date")

        return uil.attached_media.local_url if uil and uil.attached_media else None

    @api.model
    def get_image_order(self,token):
        sb_data = self.env['fsl.lesson.storyboard'].search([
            ('survey_user_line.user_input_id.token', '=', token),
            ('survey_user_line.question_id', '=', self.id),
        ], order="sequence asc")

        return sb_data or self.story_images

    @api.one
    def get_storyboard(self, attachment_id, token):
        # Get only the latest user_input_line. if user answered multiple times
        uil = self.env['survey.user_input_line'].search([
            ('user_input_id.token', '=', token),
            ('question_id', '=', self.id),
            ('page_id', '=', self.page_id.id),
        ], limit=1, order="create_date")
        
        sb_data = self.env['fsl.lesson.storyboard'].search([
            ('story_image', '=', attachment_id),
            ('survey_user_line', '=', uil.id),
        ], limit=1, order="create_date")

        return {
            "img_id" : attachment_id,
            "title_val" : sb_data.title or "",
            "desc_val" : sb_data.description or "",
        }

    @api.model
    def get_single_textbox_ans(self):
        labels = self.labels_ids
        if labels:
            answer = str.join(',', labels.filtered(lambda rec: rec.quizz_mark > 0).mapped('value'))
            if not answer:
                return "No right answer assigned"
            return answer
        return "No assigned Answer"
