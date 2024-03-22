# -*- coding: utf-8 -*-
import base64
import json
import logging
import os
import random
import uuid


from datetime import datetime
import werkzeug.utils

import odoo.addons.survey.controllers.main as survey_controller

from odoo import http
from odoo import http, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)


class WebsiteSurveyExtension(survey_controller.WebsiteSurvey):
    """
    Overriding of `submit` method in the WebsiteSurvey Controller
    Controller https://github.com/odoo/odoo/blob/11.0/addons/survey/controllers/main.py
    """

    # AJAX submission of a page
    @http.route(['/survey/submit/<model("survey.survey"):survey>'], type='http', methods=['POST'], auth='public', website=True)
    def submit(self, survey, **post):
        """
        Sends a notification to the evaluator about a lesson that needs to be evaluated.
        Applicable to both teacher and student (peer) evaluators.
        """
        def send_evaluation_notification(self, user_input_evaluation):
            MailMessage = request.env['mail.message']
            MailChannel = request.env['mail.channel']
            student_obj = request.env['op.student']
            faculty_obj = request.env['op.faculty']

            MailNotification = request.env['mail.notification']
            sender_id = request.env.ref('flyt_school.jesi_bot_partner_0')

            # Chances of recipient id being false is when current user is Administrator
            recipient_id = user_input_evaluation.evaluator or request.env.user.partner_id
            evaluatee = user_input_evaluation.user_input.partner_id

            # Student or Teacher reciepient
            sot_recipient = student_obj.search([
                ('user_id.partner_id', '=', recipient_id.id)
            ], limit=1)
            
            if not sot_recipient:
                sot_recipient = faculty_obj.search([
                    ('user_id.partner_id', '=', recipient_id.id)
                ], limit=1)
            
            
            student_evaluatee = student_obj.search([
                ('user_id.partner_id', '=', evaluatee.id)
            ])
            
            lesson = user_input_evaluation.lesson
            evaluation_url = user_input_evaluation.evaluation_url
            html_message_body = ('<p>Hello buddy {recipient}, '
                'you have been chosen to evaluate '
                'for the lesson <b>{lesson}</b>, '
                'please click <a href="{evaluation_url}" '
                'target="_blank">'
                '<b>here</b></a> to take you '
                'to the evaluation page.').format(
                recipient="{} {}".format(sot_recipient.name, sot_recipient.last_name),
                evaluatee="{} {}".format(student_evaluatee.name, student_evaluatee.last_name),
                lesson=lesson,
                evaluation_url=evaluation_url
            )
            mail_channel_name = "JESI-{}{}".format(recipient_id.name, recipient_id.id)
            mail_channel = MailChannel.sudo().search([
                ('name', '=', mail_channel_name),
            ])

            if not mail_channel:
                vals = {
                    'name': mail_channel_name,
                    'channel_type': u'chat',
                    'public': u'private',
                    'channel_partner_ids': [(6, _, [sender_id.id, recipient_id.id])],
                    'channel_last_seen_partner_ids': [
                        (0, _, {
                            'partner_id': sender_id.id,
                            'partner_email': sender_id.email
                        }),
                        (0, _, {
                            'partner_id': recipient_id.id,
                            'partner_email': recipient_id.email
                        })
                    ]
                }
                mail_channel = MailChannel.sudo().create(vals)

            vals = {
                'subject': u'Lesson Evaluation',
                'message_type': u'comment',
                'body': html_message_body,
                'author_id': sender_id.id,
                'model': u'mail.channel',
                'res_id': mail_channel.id,
                'channel_ids': [(4, mail_channel.id, _)]
            }

            mail_message = MailMessage.sudo().create(vals)

        """
        Retrieves all partners of the current user from all classes that
        contains the lesson where the question belongs to.
        """

        def get_partners(self, survey, post, partner_id, lesson_evaluation_type):
            # Initialize empty `op.student` recordset
            partners = request.env['res.partner']
            # Retrieves all classes that the survey subject belongs to
            classes = request.env['fs.class'].sudo().search([('subject_id', '=', survey.subject_id.id)])
            # Looping through all classes to get all the other students that also belong to the same class
            for class_object in classes:
                # If current student belongs to class, get all the partners
                if partner_id in class_object.sudo().student_ids.mapped('partner_id').ids:
                    if lesson_evaluation_type in ['peer_to_peer', 'peer_to_peer_teacher']:
                        # Adding the current partners to the `partners` recordset
                        partners |= class_object.sudo().student_ids.filtered(
                            lambda record: record.partner_id.id != partner_id
                        ).mapped('partner_id')
                    if lesson_evaluation_type == 'teacher':
                        # Adding the current partners to the `partners` recordset
                        partners |= class_object.faculty_id.partner_id
            return partners

        """
        Assigns random evaluators to the question if the evaluation type is `peer_to_peer`.
        """

        def assign_evaluators(self, survey, post, user_id, user_input):
            count = survey.evaluators_count

            user_input_evaluations = request.env['fsl.user_input_evaluation'].sudo().search(
                [('user_input', '=', user_input.id)])

            vals = {'user_input': user_input.id}
            lesson_evaluation_type = survey.lesson_evaluation_type
            partners = get_partners(
                self, survey, post, user_input.partner_id.id, lesson_evaluation_type)

            if lesson_evaluation_type in ['peer_to_peer', 'peer_to_peer_teacher']:
                evaluators_count = count if len(partners) >= count else len(partners)
                for i in range(evaluators_count):
                    random_evaluator = random.choice(partners)
                    vals.update({'evaluator': random_evaluator.id})
                    uie_old = request.env['fsl.user_input_evaluation'].sudo().search([
                        ('user_input', '=', user_input.id),
                        ('evaluator', '=', random_evaluator.id)
                    ])
                    if not uie_old:
                        uie = user_input_evaluations.sudo().create(vals)
                        send_evaluation_notification(self, uie)
                    partners -= random_evaluator

            # Add a teacher as evaluator aside from the five randomly selected peers if `lesson_evaluation_type` is 'peer_to_peer_teacher'
            if lesson_evaluation_type == 'peer_to_peer_teacher':
                teacher = get_partners(self, survey, post, user_input.partner_id.id, 'teacher')
                vals.update({'evaluator': teacher.id})
                uie_old = request.env['fsl.user_input_evaluation'].sudo().search([
                    ('user_input', '=', user_input.id),
                    ('evaluator', '=', teacher.id)
                ])
                if not uie_old:
                    uie = user_input_evaluations.sudo().create(vals)
                    send_evaluation_notification(self, uie)

            if lesson_evaluation_type == 'teacher':
                vals.update({'evaluator': partners.id})
                uie_old = request.env['fsl.user_input_evaluation'].sudo().search([
                    ('user_input', '=', user_input.id),
                    ('evaluator', '=', partners.id)
                ])
                if not uie_old:
                    uie = request.env['fsl.user_input_evaluation'].sudo().create(vals)
                    send_evaluation_notification(self, uie)

        _logger.debug('Incoming data: %s', post)
        page_id = int(post['page_id'])
        questions = request.env['survey.question'].search([('page_id', '=', page_id)])

        # Answer validation
        errors = {}
        for question in questions:
            answer_tag = "%s_%s_%s" % (survey.id, page_id, question.id)
            errors.update(question.validate_question(post, answer_tag))

        ret = {}
        if len(errors):
            # Return errors messages to webpage
            ret['errors'] = errors
        else:
            # Store answers into database
            try:
                user_input = request.env['survey.user_input'].sudo().search(
                    [('token', '=', post['token'])], limit=1)
            except KeyError:  # Invalid token
                return request.render("website.403")
            user_id = request.env.user.id if user_input.type != 'link' else SUPERUSER_ID

            for question in questions:
                answer_tag = "%s_%s_%s" % (survey.id, page_id, question.id)
                request.env['survey.user_input_line'].sudo(user=user_id).save_lines(
                    user_input.id, question, post, answer_tag)

            go_back = post['button_submit'] == 'previous'
            next_page, _, last = request.env['survey.survey'].next_page(
                user_input, page_id, go_back=go_back)
            vals = {'last_displayed_page_id': page_id}
            if next_page is None and not go_back:
                vals.update({'state': 'done', 'time_end': datetime.now()})
                # Calls the `assign_evaluators` method to check if the `lesson_evaluation_type` is 'peer_to_peer' and assign evaluators
                assign_evaluators(self, survey, post, user_id, user_input)
            else:
                vals.update({'state': 'skip'})
            user_input.sudo(user=user_id).write(vals)
            ret['redirect'] = '/survey/fill/%s/%s' % (survey.id, post['token'])
            if go_back:
                ret['redirect'] += '/prev'
        return json.dumps(ret)

    # Override viewing of results
    @http.route(['/survey/results/<model("survey.survey"):survey>'],
                type='http', auth='user', website=True)
    def survey_reporting(self, survey, token=None, **post):
        result_template = 'survey.result'
        current_filters = []
        filter_display_data = []
        filter_finish = False

        if not survey.user_input_ids or not [input_id.id for input_id in survey.user_input_ids if input_id.state != 'new']:
            result_template = 'survey.no_result'
        if 'finished' in post:
            post.pop('finished')
            filter_finish = True
        if post or filter_finish:
            if 'viewall-survey' in post:
                post.pop('viewall-survey')
            else:
                filter_data = self.get_filter_data(post)
                current_filters = survey.filter_input_ids(filter_data, filter_finish)
                filter_display_data = survey.get_filter_display_data(filter_data)
        else:
            current_filters = request.env['survey.user_input'].search([
                    ('survey_id', '=', survey.id),
                    ('partner_id', '!=', False)
                ]).ids
            if not current_filters:
                result_template = 'survey.no_result'
        return request.render(result_template,
                                      {'survey': survey,
                                       'survey_dict': self.prepare_result_dict(survey, current_filters),
                                       'page_range': self.page_range,
                                       'current_filters': current_filters,
                                       'filter_display_data': filter_display_data,
                                       'filter_finish': filter_finish
                                       })
    
    # Go back to `Lessons to Evaluate`
    @http.route(['/lesson/evaluate'], type='http', auth='public')
    def go_to_lessons_to_evaluate(self, **post):
        action = request.env.ref('flyt_school_lessons.act_open_evaluations_student_view').id
        url = "/web?#view_type=list&model=fsl.user_input_evaluation&action={0}".format(
            action)
        return werkzeug.utils.redirect(url)

    # Go back to `Evaluations`
    @http.route(['/lesson/evaluations'], type='http', auth='public')
    def go_to_evaluations(self, **post):
        active_id = request.env['op.student'].sudo().search(
            [('partner_id', '=', request.env.user.partner_id.id)]).id
        url = "/web?#id={}&view_type=form&model=op.student".format(
            active_id)
        return werkzeug.utils.redirect(url)

    # Lesson evaluation displaying
    @http.route(['/lesson/evaluate/<model("fsl.user_input_evaluation"):user_input_evaluation>'], type='http', auth='public', website=True)
    def evaluate(self, user_input_evaluation, **post):
        """Display the evaluation view of the lesson answers"""
        partner_id = request.env.user.partner_id
        evaluator_partner_id = user_input_evaluation.evaluator
        user_input_id = user_input_evaluation.user_input
        remarks_visibilty = True
        user = request.env.user
        faculty = request.env.ref('openeducat_core.group_op_faculty')

        if faculty.id not in user.groups_id.ids:
            remarks_visibilty = False
        # If currently logged in user is not the evaluator, return forbidden
        if partner_id != evaluator_partner_id and user.id != SUPERUSER_ID:
            return request.render('website.403')
        
        page, page_nr, last, max_page = user_input_evaluation.next_page(
                user_input_id,
                0,
                go_back=False
        )

        input_evaluations, eval_type, evaluations, token = user_input_evaluation.load_eval_line(page)
        
        return request.render('flyt_school_lessons.evaluation_view', {
            'user_evaluation_criteria': user_input_id.survey_id.evaluation_criteria,
            'user_input_evaluation': user_input_evaluation,
            'user_input_line_evaluations': input_evaluations,
            'user_input_evaluation_type': eval_type,
            'evaluations': evaluations,
            'remarks_visibilty': remarks_visibilty,
            'token': token,
            'fsl_not_editable': True,
            'page_nr': page_nr,
            'max_page': max_page,
            'page': page,
        })

    # Saving of the evaluations for the user_input_evaluation
    @http.route(['/lesson/evaluate/<model("fsl.user_input_evaluation"):user_input_evaluation>/save'], type='http', auth='public', website=True)
    def save_evaluations(self, user_input_evaluation, **post):
        # user_input_evalution is actually user_input_line or fsl.input_line_evaluation
        button_status = post.get('submit_evaluations_button')

        if button_status == 'back_to_evaluations':
            return werkzeug.utils.redirect('/lesson/evaluate')

        user_input_evaluation.save_eval_line(post, button_status)

        if button_status in ['next_page', 'previous']:
            page_id = int(post.get('page_id'))
            partner_id = request.env.user.partner_id
            evaluator_partner_id = user_input_evaluation.evaluator
            user_input_id = user_input_evaluation.user_input
            remarks_visibilty = True
            user = request.env.user
            faculty = request.env.ref('openeducat_core.group_op_faculty')

            if faculty.id not in user.groups_id.ids:
                remarks_visibilty = False
            # If currently logged in user is not the evaluator, return forbidden
            if partner_id != evaluator_partner_id and user.id != SUPERUSER_ID:
                return request.render('website.403')

            page, page_nr, last, max_page = user_input_evaluation.next_page(
                user_input_id,
                page_id,
                go_back=button_status == 'previous'
            )
            eval_icons = request.env['fs.evaluation'].sudo().search([])
            
            input_evaluations, eval_type, evaluations, token = user_input_evaluation.load_eval_line(page)
            return request.render('flyt_school_lessons.evaluation_view', {
                'user_evaluation_criteria': user_input_id.survey_id.evaluation_criteria,
                'user_input_evaluation': user_input_evaluation,
                'user_input_line_evaluations': input_evaluations,
                'user_input_evaluation_type': eval_type,
                'eval_icons': eval_icons,
                'evaluations': evaluations,
                'remarks_visibilty': remarks_visibilty,
                'token': token,
                'fsl_not_editable': True,
                'page_nr': page_nr,
                'max_page': max_page,
                'page': page,
            })
        else:
            return request.render('flyt_school_lessons.evaluation_submitted_view', {'user_input_evaluation': user_input_evaluation})

    # Lesson evaluation results viewing
    @http.route(['/evaluation/<model("survey.user_input"):user_input>/result'], type='http', auth='public', website=True)
    def view_evaluation_results(self, user_input, **post):
        """Display evaluatee lesson result"""
        UserInputLineEvaluation = request.env['fsl.input_line_evaluation']
        UserInputEvaluation = request.env['fsl.user_input_evaluation']
        classes = request.env['fs.class'].sudo().search([('subject_id', '=', user_input.survey_id.subject_id.id)])
        user_input_evaluation = UserInputEvaluation.sudo().search([('user_input', '=', user_input.id)], limit=1)
        user_input_id = user_input_evaluation.user_input
        eval_icons = request.env['fs.evaluation'].sudo().search([])

        evaluation_types = request.env['fs.evaluation'].sudo().search([])
        user_input_lines = user_input.user_input_line_ids
        evaluations_summary = []
        evaluations = []
        
        input_evaluations = UserInputLineEvaluation.sudo().search(
                [('user_input_evaluation', '=', user_input_evaluation.id)])

        user = request.env['op.student'].sudo().search([('partner_id', '=', user_input.partner_id.id)])
        for user_input_line in user_input_lines:
            uile_evaluations = []
            user_input_line_evaluations = UserInputLineEvaluation.sudo().search(
                [('user_input_line', '=', user_input_line.id)])
            for evaluation_type in evaluation_types:
                evaluation_count = len(user_input_line_evaluations.sudo().filtered(
                    lambda uile: uile.evaluator_evaluation == evaluation_type))
                uile_evaluations.append({
                    'evaluation': evaluation_type,
                    'evaluation_count': evaluation_count
                })

            evaluations.append({
                'user_input_line': user_input_line,
                'user_input_line_evaluations': uile_evaluations
            })

        for evaluation_type in evaluation_types:
            total_count = 0
            for evaluation in evaluations:
                user_input_line_evaluations = evaluation['user_input_line_evaluations']
                for uile in user_input_line_evaluations:
                    if uile['evaluation'] == evaluation_type:
                        total_count += uile['evaluation_count']
            evaluations_summary.append({
                'evaluation': evaluation_type,
                'total_count': total_count
            })

        return request.render('flyt_school_lessons.evaluation_evaluatee_view', {
            'user_evaluation_criteria': user_input_id.survey_id.evaluation_criteria,
            'user_input_evaluation': user_input_evaluation,
            'user_input_line_evaluations': input_evaluations,
            'user_input_evaluation_type': user_input_evaluation.sudo().user_input.survey_id.lesson_evaluation_type,
            'evaluations_summary': evaluations_summary,
            'evaluations': evaluations,
            'eval_icons': eval_icons,
            'user': user,
            'token': user_input.token,
            'fsl_not_editable': True,
        })

    # Override survey controller during start
    @http.route(['/survey/start/<model("survey.survey"):survey>',
                 '/survey/start/<model("survey.survey"):survey>/<string:token>'],
                type='http', auth='public', website=True)
    def start_survey(self, survey, token=None, **post):
        UserInput = request.env['survey.user_input']

        # Test mode
        if token and token == "phantom":
            _logger.info("[survey] Phantom mode")
            user_input = UserInput.create({'survey_id': survey.id, 'test_entry': True})
            data = {'survey': survey, 'page': None, 'token': user_input.token}
            return request.render('survey.survey_init', data)
        # END Test mode

        # Controls if the survey can be displayed
        errpage = self._check_bad_cases(survey, token=token)
        if errpage:
            return errpage

        # Manual surveying
        if not token:
            vals = {'survey_id': survey.id}
            if request.website.user_id != request.env.user:
                vals['partner_id'] = request.env.user.partner_id.id

            # To restrict multiple user_input each user per survey.
            user_input = UserInput.sudo().search([
                ('partner_id', '=', vals.get('partner_id')),
                ('survey_id', '=', survey.id)
            ])

            # Checks if user_input exist and token was not assigned
            if user_input and not user_input.token:
                user_input.write({'token': str(uuid.uuid4())})
            # if no user_input, create new user_input
            elif not user_input:
                user_input = UserInput.create(vals)
            # if user user_input exist and has a token. do nothing
        else:
            user_input = UserInput.sudo().search([('token', '=', token)], limit=1)
            if not user_input:
                return request.render("website.403")


        # Do not open expired survey
        errpage = self._check_deadline(user_input)
        if errpage:
            return errpage

        # Select the right page
        if user_input.state == 'new':  # Intro page
            data = {'survey': survey, 'page': None, 'token': user_input.token}
            return request.render('survey.survey_init', data)
        else:
            return request.redirect('/survey/fill/%s/%s' % (survey.id, user_input.token))

    # Override survey controller for survey displaying
    @http.route(['/survey/fill/<model("survey.survey"):survey>/<string:token>',
                 '/survey/fill/<model("survey.survey"):survey>/<string:token>/<string:prev>'],
                type='http', auth='public', website=True)
    def fill_survey(self, survey, token, prev=None, **post):
        '''Display and validates a survey'''
        Survey = request.env['survey.survey']
        UserInput = request.env['survey.user_input']

        # Controls if the survey can be displayed
        errpage = self._check_bad_cases(survey)
        if errpage:
            return errpage

        # Load the user_input
        user_input = UserInput.sudo().search([('token', '=', token)], limit=1)
        if not user_input:  # Invalid token
            return request.render("website.403")

        # Do not display expired survey (even if some pages have already been
        # displayed -- There's a time for everything!)
        errpage = self._check_deadline(user_input)
        if errpage:
            return errpage

        # Select the right page
        if user_input.state == 'new':  # First page
            page, page_nr, last = Survey.next_page(user_input, 0, go_back=False)
            data = {'survey': survey, 'page': page, 'page_nr': page_nr, 'token': user_input.token}
            user_id = request.env.user.id if user_input.type != 'link' else SUPERUSER_ID
            user_input.sudo(user=user_id).write({'time_start': datetime.now()})
            if last:
                data.update({'last': True})
            return request.render('survey.survey', data)
        elif user_input.state == 'done':  # Display success message
            return request.render('survey.sfinished', {'survey': survey,
                                                       'token': token,
                                                       'user_input': user_input})
        elif user_input.state == 'skip':
            flag = (True if prev and prev == 'prev' else False)
            page, page_nr, last = Survey.next_page(
                user_input, user_input.last_displayed_page_id.id, go_back=flag)

            # special case if you click "previous" from the last page, then leave the survey, then reopen it from the URL, avoid crash
            if not page:
                page, page_nr, last = Survey.next_page(
                    user_input, user_input.last_displayed_page_id.id, go_back=True)

            data = {
                'survey': survey,
                'page': page,
                'page_nr': page_nr,
                'token': user_input.token,
            }
            if last:
                data.update({'last': True})
            return request.render('survey.survey', data)
        else:
            return request.render("website.403")

    """
    Triggered when recording for an audio/video answer type is stopped, passed in post are the following:
    - `recorded blob URL`
    - `prefix`: the unique identifier to which question the recorded answer should be assigned to
        format: %s_%s_%s' % (survey.id, page.id, question.id)
    """
    @http.route(['/answer_recording/file'], type='http', methods=['POST'], auth='public', website=True)
    def attach_recorded_file(self, **post):
        user_id = request.env.user.id
        Attachments = request.env['ir.attachment']
        media_file = post['recordedFile']
        mimetype = post['mimeType']
        unique_filename = '{}-{}'.format(user_id, media_file.filename)
        media_data = media_file.read()

        existing_files = Attachments.sudo().search([('datas_fname', '=', unique_filename)])
        if existing_files:
            for file in existing_files:
                # Removing of physical file from server filestore
                store_fname = file.store_fname
                if store_fname:
                    full_path = file._full_path(store_fname)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                # Removing of `ir.attachment` model object from database
                file.unlink()

        # Creating new `ir.attachment` and file in the filestore
        attachment_id = Attachments.create({
            'name': unique_filename,
            'mimetype': mimetype,
            'datas': base64.b64encode(media_data),
            'datas_fname': unique_filename,
            'attachment_status': 'attached'
        })

        return json.dumps({
            'message': u'Recording successfully saved. Attachment ID: {}'.format(attachment_id.id),
            'srcPath': u'{}'.format(attachment_id.local_url)
        })

    """
    Longpolling endpoint for checking whether a reaction video attachment has been processed (overlaying is done or not)
    - to return a response `processing` or `attached` status for the attachment id given
    - to be handled by `answer_recording.js`
    """
    @http.route(['/video_overlay_status/<int:attachment_id>'], type='http', methods=['GET'], auth='public', website=True)
    def check_video_overlay_status(self, attachment_id, **get):
        video_attachment = request.env['ir.attachment'].sudo().search([('id', '=', attachment_id)])
        return json.dumps({
            'attachmentId': attachment_id,
            'attachmentStatus': video_attachment.attachment_status
        })
