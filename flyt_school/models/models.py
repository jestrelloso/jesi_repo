# -*- coding: utf-8 -*-
import uuid

from lxml import etree

from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
from openerp.osv.orm import setup_modifiers


class Semester(models.Model):
    _name = 'fs.semester'

    name = fields.Char(string="Name", required=True)
    start_date = fields.Date(string="Start Date", default=fields.Date.today)
    end_date = fields.Date(string="End Date")


class Day(models.Model):
    _name = 'fs.day'
    _rec_name = 'day'

    day = fields.Char(string="Day", readonly=True)


class Class(models.Model):
    _name = 'fs.class'
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)
    subject_id = fields.Many2one('op.subject', string="Subject")
    semester_id = fields.Many2one('fs.semester', string="Semester")
    start_time = fields.Float(string="Time Start", help="24-Hour Format")
    end_time = fields.Float(string="Time End", help="24-Hour Format")
    day_ids = fields.Many2many('fs.day', string="Scheduled Days")
    student_ids = fields.Many2many('op.student', string="Students")
    faculty_id = fields.Many2one('op.faculty', string="Faculty")
    faculty_user_id = fields.Many2one(related='faculty_id.user_id', string="Faculty User ID")
    department_id = fields.Many2one('fs.department', string="Department")
    section_id = fields.Many2one('fs.section', string="Section")

    _sql_constraints = [
        ('unique_class_name',
         'unique(name)', 'Name should be unique per class'),
    ]

    @api.model
    def fields_view_get(self, view_id=None, view_type='tree', context=None,
                        toolbar=False, submenu=False):
        result = super(Class, self).fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu
        )
        doc = etree.fromstring(result['arch'])
        user = self.env.user
        admin = self.env.ref('openeducat_core.group_op_back_office')

        if admin.id not in user.groups_id.ids:
            if view_type == 'form':
                field_list = [
                    doc.xpath("//field[@name='name']"),
                    doc.xpath("//field[@name='subject_id']"),
                    doc.xpath("//field[@name='day_ids']"),
                    doc.xpath("//field[@name='faculty_id']"),
                    doc.xpath("//field[@name='start_time']"),
                    doc.xpath("//field[@name='end_time']"),
                    doc.xpath("//field[@name='semester_id']"),
                    doc.xpath("//field[@name='section_id']")
                ]
                for field in field_list:
                    if field:
                        field[0].attrib['readonly'] = 'True'
                        setup_modifiers(field[0], {})
                student_ids = doc.xpath("//field[@name='student_ids']")
                if student_ids:
                    student_ids[0].attrib['options'] = "{'no_create': True}"

        result['arch'] = etree.tostring(doc)

        return result

    @api.onchange('section_id')
    def onchange_section_id(self):
        # Adds student in the class if student is not yet in the class
        for student in self.section_id.student_ids:
            if student not in self.student_ids:
                self.student_ids += student

        # Removes student in the class if student belongs to the previous saved/selected section
        if self._origin.section_id != self.section_id and self._origin:
            for student in self._origin.section_id.student_ids:
                if student in self.student_ids:
                    self.student_ids -= student

    @api.onchange('department_id')
    def _get_section_ids(self):
        if self.department_id:
            return {
                'domain': {
                    'section_id': [('department_id', '=', self.department_id.id)]
                }
            }

    @api.constrains('student_ids')
    def _check_student_classes(self):
        students = []
        for record in self.student_ids:
            student_duplicate_class_count = self.env["fs.class"].search_count([
                ('subject_id', '=', self.subject_id.id),
                ('student_ids', 'in', record.id)
            ])
            if student_duplicate_class_count > 1:
                students.append("{} {}".format(
                    record.name,
                    record.last_name
                ))
        if students:
            raise ValidationError(_("The following students already have an existing class with the same subject ({}): \n {}").format(
                self.subject_id.name, "\n".join(students)))

    @api.constrains('start_time', 'end_time')
    def _validate_time(self):
        if self.start_time >= 24.0 or self.end_time >= 24.0:
            raise ValidationError(_("Time Start/End cannot exceed to 24:00 or higher. It's only from 00:00 to 23:00"))


class Evaluation(models.Model):
    """
    Evaluation model to handle dynamic evaluation remarks for point scoring
    system: e.g. `Like` - 3 pts, `Love` - 5 pts, `Sad` - 1 pt, etc.
    """
    _name = 'fs.evaluation'
    _rec_name = 'name'

    name = fields.Char(string='Evaluation Remark', required=True)
    value = fields.Float(compute='_get_current_evaluation_value')
    icon = fields.Binary(
        string='Icon', help='This is the icon to be displayed for the evaluation.')
    small_icon = fields.Binary(string='Icon', compute='_get_small_icon')
    value_ids = fields.One2many(
        'fs.evaluation_value', 'evaluation_id', string='Evaluation Value')
    attach_icon = fields.Many2one('ir.attachment', string="Attached Icon")
    icon_attachment_display = fields.Html(string="Icon", compute='_get_icon_attachment_display_url')
    description = fields.Char(string="Description")
    evaluation_color = fields.Char(string='Color') 
    
    @api.one
    def _get_icon_attachment_display_url(self):
        html = "<img class='img img-responsive' style='height: 36px' src='/web/content/{}'"
        self.icon_attachment_display = html.format(self.attach_icon.id)
    
    @api.model
    def create(self, vals):
        if 'icon' in vals:
            vals = self._attached_icon(vals)
        return super(Evaluation, self).create(vals)

    @api.multi
    def write(self, vals):
        for rec in self:
            if 'icon' in vals:
                vals = self._attached_icon(vals)
            super(Evaluation, self).write(vals)
        return True

    @api.one
    @api.depends('value_ids')
    def _get_current_evaluation_value(self):
        if len(self.value_ids) is not 0:
            self.value = self.value_ids[0].value
        else:
            self.value = 0.0

    @api.model
    def _attached_icon(self, vals):
        Attachments = self.env['ir.attachment']
        if self.attach_icon:
            self.attach_icon.write({
                'data': vals.get('icon', False)
            })
        else:
            unique_filename = str(uuid.uuid1())
            attach_icon = Attachments.create({
                'name': unique_filename,
                'mimetype': 'image/png',
                'datas': vals.get('icon', False),
                'data_fname': unique_filename
            })
            vals['attach_icon'] = attach_icon.id
        return vals

    @api.model
    def cron_convert_icon_to_attachment(self):
        Attachments = self.env['ir.attachment']
        evaluations = self.search([])
        for rec in evaluations:
            unique_filename = str(uuid.uuid1())
            icon_vals = {
                'name': unique_filename,
                'datas_fname': unique_filename,
                'mimetype': 'image/png',
                'datas': rec.icon
            }
            attach_icon = Attachments.create(icon_vals)
            rec.write({'attach_icon': attach_icon.id})

    @api.multi
    @api.depends('icon')
    def _get_small_icon(self):
        for rec in self:
            rec.small_icon = tools.image_resize_image(rec.icon, size=(36, 36))


class EvaluationValue(models.Model):
    _name = 'fs.evaluation_value'
    _order = 'create_date desc'
    _rec_name = 'evaluation_id'

    evaluation_id = fields.Many2one('fs.evaluation')
    value = fields.Float(string='Evaluation Value', required=True)


class EvaluationCriteria(models.Model):
    _name = 'fs.evaluation_criteria'

    criteria = fields.Html(string='Criteria')


class Section(models.Model):
    _name = 'fs.section'
    _rec_name = 'code'

    code = fields.Char(string="Code", required=True)
    student_ids = fields.One2many('op.student', 'section_id', string="Students")
    department_id = fields.Many2one('fs.department', string="Department")

    _sql_constraints = [
        ('unique_section_code',
         'unique(code)', 'Code should be unique per section'),
    ]


class Department(models.Model):
    _name = 'fs.department'

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)
    section_ids = fields.One2many('fs.section', 'department_id', string="Section")
    student_ids = fields.One2many('op.student', 'department_id', string="Students")
    college_id = fields.Many2one('fs.college', string="College")

    _sql_constraints = [
        ('unique_department_code',
         'unique(code)', 'Code should be unique per department'),
        ('unique_department_name',
         'unique(name)', 'Name should be unique per department'),
    ]

    @api.depends('name, code')
    def name_get(self):
        result = []
        sorted_result = []
        for rec in self:
            name = "{} / {}".format(rec.code, rec.name)
            result.append((rec.id, name))
        sorted_result = sorted(result, key=lambda tup: (tup[1]))
        return sorted_result


class College(models.Model):
    _name = 'fs.college'
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)
    department_ids = fields.One2many('fs.department', 'college_id', string="Departments")

    _sql_constraints = [
        ('unique_department_code',
         'unique(code)', 'Code should be unique per department'),
        ('unique_department_name',
         'unique(name)', 'Name should be unique per department'),
    ]
