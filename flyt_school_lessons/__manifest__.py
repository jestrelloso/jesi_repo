# -*- coding: utf-8 -*-
{
    'name': "flyt_school_lessons",

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
    'depends': ['base', 'survey', 'web', 'flyt_school'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'data/cron_data.xml',
        'views/views.xml',
        'views/overlay_config.xml',
        'views/evaluation_report.xml',
        'views/inherited_class_views.xml',
        'views/inherited_subject_views.xml',
        'views/inherited_survey_views.xml',
        'views/inherited_survey_templates.xml',
        'views/inherited_survey_question_views.xml',
        'views/class_lesson_views.xml',
        'views/lesson_group_views.xml',
        'views/inherited_student_views.xml',
        'views/evaluation_templates.xml',
        'security/fsl_security.xml',
        'static/src/xml/resources.xml',
        'templates/lesson_html_field_answer_type.xml',
        'templates/terms_and_condition.xml',
        'views/master_evaluations_views.xml',
        'security/inherited_survey_security.xml',
        'security/inherited_op_security.xml'
    ],
    'qweb': [
        'static/src/xml/inherited_base.xml',
    ],

    'qweb':[
        'static/src/xml/*.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
}
