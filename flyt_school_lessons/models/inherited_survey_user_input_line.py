import logging
import datetime
import pytz

from odoo import models, fields, api

from ..utils.fsl_ffmpeg_utils import ReactionVideoOverlayer as _overlayer


_logger = logging.getLogger(__name__)


class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input_line'

    evaluations = fields.One2many('fsl.input_line_evaluation', 'user_input_line', string="Evaluations")
    attached_media = fields.Many2one('ir.attachment', string='Attached Media Answer', help='Audio/Video recording answer.')
    answer_type = fields.Selection(selection_add=[
        ('audio_input', 'Audio Input (audio recording)'),
        ('video_input', 'Video Input (video recording)'),
        ('storyboard_type', 'Storyboard Type')
    ])
    story_images = fields.One2many('fsl.lesson.storyboard', 'survey_user_line')

    @api.multi
    def save_lines(self, user_input_id, question, post, answer_tag):
        save_lines = super(SurveyUserInputLine, self).save_lines(user_input_id, question, post, answer_tag)
        
        if save_lines != False:
            curr_user = self.env.user
            if question.add_to_profile and curr_user:
                student_rec = self.env['op.student'].sudo().search([('user_id', '=', curr_user.id)])
                if student_rec:
                    if question.type == 'video_input':
                        Attachments = self.env['ir.attachment']
                        unique_filename = '{}-{}'.format(curr_user.id, answer_tag)
                        attachment_answer = Attachments.sudo().search([('datas_fname', '=', unique_filename)], limit=1)
                        value = attachment_answer.id
                    else:
                        value = post.get(answer_tag)
                    student_rec.sudo().write({question.student_fields: value})

    @api.model
    def get_mark_textbox(self, vals):
        value_text = vals.get('value_text', '')
        quiz_mark = 0.0

        if value_text:
            # suggested answers for this field
            # Answers order will be based on how the survey label was arranged.
            suggested_values = self.env['survey.label'].search([
                ('question_id', '=', vals.get('question_id', self.question_id.id))
            ], order='sequence')
            # User input values in textbox separated by comma
            uiv = value_text.strip().split(',')
            for index, answer in enumerate(suggested_values):
                try:
                    quiz_mark += answer.quizz_mark if answer.value.strip() == uiv[index].strip() else 0.0
                except (IndexError):
                    # Ignore index Error. this will occur is user input is more or less than the
                    # suggested value or right answers.
                    pass
        vals.update({'quizz_mark': quiz_mark})
        return vals

    @api.multi
    def write(self, vals):
        for rec in self:
            survey = rec.env['survey.survey'].browse([vals.get('survey_id', rec.survey_id.id)])
            if vals.get('answer_type') == 'text' and survey.lesson_evaluation_type == 'system_generated':
                vals = self.get_mark_textbox(vals)
            super(SurveyUserInputLine, self).write(vals)

        return True

    @api.model
    def create(self, vals):
        survey = self.env['survey.survey'].browse([vals.get('survey_id', self.survey_id.id)])
        if vals.get('answer_type') == 'text' and survey.lesson_evaluation_type == 'system_generated':
            vals = self.get_mark_textbox(vals)

        return super(SurveyUserInputLine, self).create(vals)

    @api.model
    def attach_answer_recording(self, user_input_id, question, post, answer_tag, answer_type):
        user_id = self.env.user.id
        Attachments = self.env['ir.attachment']
        unique_filename = '{}-{}'.format(user_id, answer_tag)
        attachment_answer = Attachments.sudo().search([('datas_fname', '=', unique_filename)], limit=1)
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'survey_id': question.survey_id.id,
            'skipped': False,
        }
        
        if attachment_answer:
            vals.update({
                'answer_type': answer_type,
                'attached_media': attachment_answer.id
            })
        else:
            vals.update({'answer_type': None, 'skipped': True})
        old_uil = self.search([
            ('user_input_id', '=', user_input_id),
            ('survey_id', '=', question.survey_id.id),
            ('question_id', '=', question.id)
        ])
        if old_uil:
            old_uil.write(vals)
        else:
            old_uil = old_uil.create(vals)

        # Calls the overlayer Class to overlay the question video on top of the reaction video
        if question.is_reaction_video:
            attachment_answer.sudo().write({'attachment_status': 'to_process'})
            # environment = self.env
            # environment.cr.commit()
            # self._overlay_video(environment, old_uil, question, video_reaction=attachment_answer)

        return True

    @api.model
    def _overlay_video_cron(self, use_hw_accel=False):
        tz_of_responsible_user = self.env.user.partner_id.tz or self._context.get('tz')
        timezone = pytz.timezone(tz_of_responsible_user or 'UTC')

        datetime_now = datetime.datetime.now(timezone)
        current_weekday = datetime_now.isoweekday()
        
        time_now = datetime_now.strftime("%H:%M")
        computed_limit = 0

        process_config = self.env['fsl.overlay.config'].search([
            ('time_start', '<=', time_now),
            ('time_end', '>=', time_now),
            # operator '&' and '|' are function that accepts 2 arguements or arity 2
            # wdf = weekday_from, wdt = weekday_to, cwd = current_weekday
            # if (wdf <= cwd & wdt >= cwd) or (wdf > wdt & wdt >= cwd) or (wdf = cwd and wdt = cwd-1)
            '|',
            '|',
            '&',
            ('weekday_from', '<=', current_weekday),
            ('weekday_to', '>=', current_weekday),
            '&',
            ('is_from_gt_to', '=', True),
            ('weekday_to', '>=', current_weekday),
            '&',
            ('weekday_from', '=', current_weekday),
            ('weekday_to', '=', current_weekday - 1 if current_weekday != 1 else 7),
        ])

        for conf in process_config:
            computed_limit += conf.no_of_batch_to_process

        if process_config:
            video_process_count = self.env['survey.user_input_line'].search_count([
                ('question_id.is_reaction_video', '=', True),
                ('attached_media.attachment_status', '=', 'in_process')
            ])

            if video_process_count < computed_limit:
                to_process_video_count = computed_limit - video_process_count
                _logger.info("No. of Batch to process: {}".format(to_process_video_count))
                to_process_video = self.env['survey.user_input_line'].search(
                    [
                    ('question_id.is_reaction_video', '=', True),
                    ('attached_media.attachment_status', '=', 'to_process')
                ], limit=to_process_video_count, order='date_create asc')

                if to_process_video:
                    attach_media = to_process_video.mapped('attached_media').write({
                        'attachment_status': 'in_process'
                    })
                    self.env.cr.commit()

                    for vid in to_process_video:
                        _overlayer(self.env, vid, vid.question_id, vid.attached_media, use_hw_accel)

    @api.model
    def save_line_audio_input(self, user_input_id, question, post, answer_tag):
        return self.attach_answer_recording(user_input_id, question, post, answer_tag, 'audio_input')

    @api.model
    def save_line_video_input(self, user_input_id, question, post, answer_tag):
        return self.attach_answer_recording(user_input_id, question, post, answer_tag, 'video_input')

    @api.model
    def save_line_storyboard_type(self, user_input_id, question, post, answer_tag):
        def get_image_key(question_data, post_items):
            unique_key_name = u"sb_{}".format(question_data.id)
            skipped = False
            data_key = []

            for key, value in post_items.items():
                if key.startswith('sb_'):
                    _, qid, _, _ = key.split('_')

                    if int(qid) == question_data.id:
                        data_key.append(key)
                        if value == '':
                            skipped = True


            return {'data_key': data_key, 'skipped': skipped}

        temp_data = get_image_key(question, post)
        sb_data_key = temp_data.get('data_key')
        skipped = temp_data.get('skipped')
        # sb_data_key = [key for key in post.keys() if key.startswith('sb_') and key.endswith('_title')]
        # story_order_data = [(key, value) for key, value in post.items() if key.startswith(unique_key_name)]
        story_obj = self.env['fsl.lesson.storyboard']
        attach_obj = self.env['ir.attachment']

        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'survey_id': question.survey_id.id,
            'skipped': False,
            'answer_type': 'storyboard_type'
        }
        
        if skipped:
            vals.update({'skipped': True, 'answer_type': None})
        
        user_input_line = self.search([
            ('user_input_id', '=', user_input_id),
            ('survey_id', '=', question.survey_id.id),
            ('question_id', '=', question.id),
        ])

        if user_input_line:
            user_input_line.write(vals)
        else:
            user_input_line = user_input_line.create(vals)

        for key in sb_data_key:
            _, _, sequence_num, attach_id = key.split('_')
            existing_sbo = story_obj.sudo().search([
                ('survey_user_line', '=', user_input_line.id),
                ('story_image', '=', int(attach_id))
            ])

            if existing_sbo:
                existing_sbo.sudo().write({
                    'sequence': sequence_num,
                })
            else:
                existing_sbo.sudo().create({
                    'survey_user_line': user_input_line.id,
                    'story_image': attach_id,
                    'sequence': sequence_num,
                })

        return True
