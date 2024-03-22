# -*- coding: utf-8 -*-
from lxml import etree
from lxml.builder import E

from odoo import api, models, _


def name_boolean_group(id):
    return 'in_group_' + str(id)


def name_selection_groups(ids):
    return 'sel_groups_' + '_'.join(str(it) for it in ids)


class GroupsView(models.Model):
    _inherit = 'res.groups'

    @api.model
    def _update_user_groups_view(self):
        """ Modify the view with xmlid ``base.user_groups_view``, which inherits
            the user form view, and introduces the reified group fields.
        """
        if self._context.get('install_mode'):
            # use installation/admin language for translatable names in the view
            user_context = self.env['res.users'].context_get()
            self = self.with_context(**user_context)

        # We have to try-catch this, because at first init the view does not
        # exist but we are already creating some basic groups.
        view = self.env.ref('base.user_groups_view', raise_if_not_found=False)
        if view and view.exists() and view._name == 'ir.ui.view':
            group_no_one = view.env.ref('base.group_no_one')
            # Added hidden_grp to hide Hidden group
            hidden_grp = view.env['res.groups'].search([('name', '=', 'Hidden')])
            xml1, xml2 = [], []
            xml1.append(E.separator(string=_('Application Accesses'), colspan="2"))
            for app, kind, gs in self.get_groups_by_application():
                # hide groups in categories 'Hidden' and 'Extra' (except for group_no_one)
                attrs = {}
                if app.xml_id in ('base.module_category_hidden', 'base.module_category_extra', 'base.module_category_usability'):
                    attrs['groups'] = 'base.group_no_one'

                if kind == 'selection':
                    # application name with a selection field
                    if app.name == 'OpenEduCat':
                        app.name = 'Education'
                    if app.name == 'Survey':
                        app.name = 'Lessons'
                    if app.name not in ['Employees']:
                        field_name = name_selection_groups(gs.ids)
                        xml1.append(E.field(name=field_name, **attrs))
                        xml1.append(E.newline())
                else:
                    # application separator with boolean fields
                    for g in gs:
                        field_name = name_boolean_group(g.id)
                        # Added hidden_grp to hide Hidden group
                        if g == group_no_one or g == hidden_grp:
                            # make the group_no_one invisible in the form view
                            xml2.append(E.field(name=field_name, invisible="1", **attrs))
                        else:
                            xml2.append(E.field(name=field_name, **attrs))

            xml2.append({'class': "o_label_nowrap"})
            xml = E.field(E.group(*(xml1), col="2"), E.group(*(xml2), col="4"),
                          name="groups_id", position="replace")
            xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))
            xml_content = etree.tostring(xml, pretty_print=True, encoding="unicode")

            new_context = dict(view._context)
            new_context.pop('install_mode_data', None)  # don't set arch_fs for this computed view
            new_context['lang'] = None
            view.with_context(new_context).write({'arch': xml_content})
