# -*- coding: utf-8 -*-
{
    'name': "flyt_school",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'openeducat_core'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/fs_security.xml',
        'views/semester_views.xml',
        'views/evaluation_views.xml',
        'views/evaluation_value_views.xml',
        'views/evaluation_criteria_views.xml',
        'views/inherited_faculty_views.xml',
        'views/inherited_student_views.xml',
        'views/class_views.xml',
        'data/days_of_week.xml',
        'data/evaluation_types.xml',
        'data/jesi_bot.xml',
        'views/menu_navigation.xml',
        'views/inherited_webclient_templates.xml',
        'views/section_views.xml',
        'views/department_views.xml',
        'views/college_views.xml',
        'views/inherited_res_company_views.xml',
        'security/inherited_base_security.xml',
        'views/inherited_res_users_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
