# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from openerp.osv.orm import setup_modifiers
from lxml import etree
from odoo.exceptions import ValidationError


class Student(models.Model):
    _inherit = ['op.student']

    class_ids = fields.Many2many('fs.class', string="Classes")
    class_count = fields.Integer(compute='_class_count', string="Number of Classes")
    faculty_user_ids = fields.Many2many('res.users', compute='_get_faculty_ids',
                                        string="Faculty User IDs")
    faculty_user_ids_store = fields.Many2many(
        'res.users', string="Faculty User IDs Store", store=True)
    nickname = fields.Char('Nickname', size=128)
    ext_name = fields.Char('Ext')
    mobile_number = fields.Char('Mobile Number')
    year_level = fields.Selection([
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, 5),
        (6, 6),
        (7, 7),
        (8, 8),
        (9, 9),
        (10, 10),
        (11, 11),
        (12, 12),
    ], default=1)
    about_me = fields.Html('About Me')
    work_experience = fields.Html('Work Experience')
    hard_skills = fields.Html('Hard Skills')
    soft_skills = fields.Html('Soft Skills')
    hobbies = fields.Html('Hobbies/Interest')
    achievements = fields.Html('Achievements')
    desires = fields.Html('Desires')
    is_basic = fields.Boolean(default=False, compute='_is_basic')
    account_id = fields.Char('Student ID', required=True)
    section_id = fields.Many2one('fs.section', string="Section")
    department_id = fields.Many2one('fs.department', string="Department")
    street = fields.Text(string="Address", store=True)
    email = fields.Char(string="Email Address", store=True)

    def _get_faculty_ids(self):
        for record in self:
            record.faculty_user_ids = record.class_ids.mapped('faculty_user_id')

    def _class_count(self):
        self.class_count = self.env["fs.class"].search_count(
            [("student_ids", "in", self.id)])

    @api.model
    def fields_view_get(self, view_id=None, view_type='tree', context=None, toolbar=False, submenu=False):
        result = super(Student, self).fields_view_get(view_id=view_id,
                                                      view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.fromstring(result['arch'])
        user = self.env.user
        admin = self.env.ref('openeducat_core.group_op_back_office')

        if admin.id not in user.groups_id.ids:
            if view_type == 'kanban':
                kanban = doc.xpath("//kanban")
                if kanban:
                    kanban[0].set('create', '0')
            if view_type == 'tree':
                tree = doc.xpath("//tree")
                if tree:
                    tree[0].set('create', '0')
                    tree[0].attrib['delete'] = 'false'
            if view_type == 'form':
                form = doc.xpath("//form")
                if form:
                    form[0].set('create', '0')
                    form[0].set('edit', '0')
                    form[0].attrib['delete'] = 'false'
                    field_list = [
                        doc.xpath("//field[@name='image']"),
                        doc.xpath("//field[@name='name']"),
                        doc.xpath("//field[@name='middle_name']"),
                        doc.xpath("//field[@name='last_name']"),
                        doc.xpath("//field[@name='department_id']"),
                        doc.xpath("//field[@name='section_id']"),
                        doc.xpath("//field[@name='year_level']"),
                        doc.xpath("//field[@name='nickname']"),
                        doc.xpath("//field[@name='email']"),
                        doc.xpath("//field[@name='mobile_number']"),
                        doc.xpath("//field[@name='street']"),
                        doc.xpath("//field[@name='about_me']"),
                        doc.xpath("//field[@name='hobbies']"),
                        doc.xpath("//field[@name='achievements']"),
                        doc.xpath("//field[@name='desires']"),
                    ]
                    for field in field_list:
                        if field:
                            field[0].attrib['readonly'] = 'True'
                            setup_modifiers(field[0], {})

        result['arch'] = etree.tostring(doc)

        return result

    def student_list(self):
        user = self.env.user
        admin = self.env.ref('openeducat_core.group_op_back_office')
        faculty = self.env.ref('openeducat_core.group_op_faculty')
        domain = []
        if (self.env.user.has_group('openeducat_core.group_op_back_office_admin') or
                self.env.user.has_group('base.group_erp_manager')):
            domain = [(1, '=', 1)]
        elif (self.env.user.has_group('openeducat_core.group_op_student') and not
                self.env.user.has_group('openeducat_core.group_op_faculty')):
            domain = [('user_id', '=', user.id)]
        elif admin.id not in user.groups_id.ids and faculty.id in user.groups_id.ids:
            for student in self.env['op.student'].search([]):
                if student.faculty_user_ids != student.faculty_user_ids_store:
                    student.update({'faculty_user_ids_store': student.faculty_user_ids})
            domain = [('faculty_user_ids_store', '=', user.id)]
        action_data = {
            "type": "ir.actions.act_window",
            "name": "Students",
            "view_mode": "kanban,tree,form",
            "res_model": "op.student",
            "search_view_id": self.env.ref('openeducat_core.view_op_student_search').id,
            "domain": domain
        }
        return action_data

    @api.one
    def _is_basic(self):
        if self.env.user.has_group('openeducat_core.group_op_faculty'):
            self.update({'is_basic': False})
        elif self.env.user.has_group('base.group_erp_manager'):
            self.update({'is_basic': False})
        elif self.env.user.has_group('openeducat_core.group_op_back_office_admin'):
            self.update({'is_basic': False})
        elif not self.user_id:
            self.update({'is_basic': True})
        elif self.user_id.id != self.env.user.id:
            self.update({'is_basic': True})
        elif self.user_id.id == self.env.user.id:
            self.update({'is_basic': False})

    @api.model
    def create(self, vals):
        student = super(Student, self).create(vals)
        # Create a user account for student with access rights
        user_group_student = self.env.ref('openeducat_core.group_op_student')
        user_group_employee = self.env.ref('base.group_user')
        user_group_technical_features = self.env.ref('base.group_no_one')
        self.env['res.users'].create_user(
            student,
            [user_group_student.id, user_group_employee.id, user_group_technical_features.id]
        )
        return student

    @api.multi
    @api.constrains('birth_date')
    def _check_birthdate(self):
        for record in self:
            if record.birth_date and record.birth_date > fields.Date.today():
                raise ValidationError(_(
                    "Birth Date can't be greater than current date!"))

    @api.onchange('department_id')
    def _get_section_ids(self):
        if self.department_id:
            return {
                'domain': {
                    'section_id': [('department_id', '=', self.department_id.id)]
                }
            }
