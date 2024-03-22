# -*- coding: utf-8 -*-

from odoo import models, api
from openerp.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    def create_username(self, first_name, last_name, account_id):
        user_name = "{}{}{}".format(
            first_name,
            last_name,
            account_id,
        )
        user_name_formatted = ''.join(e for e in user_name if e.isalnum())
        return user_name_formatted

    @api.multi
    def create_user(self, records, user_group):
        for rec in records:
            if not rec.user_id:
                """
                Username format:
                    First name
                    Last name
                    Last 2 digits of student/faculty id (if username is taken, Last 3 digits)

                    e.g.
                    Student: Bob Smith
                    Student ID: 123456
                    Username: BobSmith56

                Password format:
                    student/faculty id
                """
                user_name = self.create_username(rec.name, rec.last_name, rec.account_id[-2:])
                existing_user = self.env['res.users'].search([('login', '=', user_name)])

                if existing_user:
                    user_name = self.create_username(rec.name, rec.last_name, rec.account_id[-3:])

                user_vals = {
                    'name': rec.name,
                    'login': user_name,
                    'password': rec.account_id,
                    'partner_id': rec.partner_id.id,
                    'groups_id': user_group
                }
                user_id = self.create(user_vals)
                rec.user_id = user_id

    @api.multi
    def write(self, vals):
        for rec in self:
            admin_user = self.env['res.users'].search([('id', '=', 1)])
            if rec.id == admin_user.id and self._uid != 1:
                raise ValidationError("You are not allowed to edit this record")
            super(ResUsers, rec).write(vals)
        return True

    def admin_access_rights(self):
        user = self.env.user
        domain = []
        if user.id != 1:
            domain = [('id', '!=', 1)]
        action_data = {
            "name": "Users",
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "view_type": "form",
            "view_mode": "tree,kanban,form",
            'views': [
                (self.env.ref('base.view_users_tree').id, 'tree'),
                (self.env.ref('base.view_res_users_kanban').id, 'kanban'),
                (self.env.ref('base.view_users_form').id, 'form'),
            ],
            "search_view_id": self.env.ref('base.view_users_search').id,
            "help": """
                Create and manage users that will connect to the system.
                Users can be deactivated should there be a period of time
                during which they will/should not connect to the system.
                You can assign them groups in order to give them specific
                access to the applications they need to use in the system.
            """,
            "context": {},
            "domain": domain
        }
        return action_data
