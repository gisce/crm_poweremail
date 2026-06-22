# -*- coding: utf-8 -*-
from __future__ import absolute_import
from oopgrade.oopgrade import MigrationHelper
from tools import config
from tools.translate import trans_load


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    module = 'crm_poweremail'
    mh = MigrationHelper(cursor, module)

    file = 'crm_data.xml'
    views = [
        'crm_poweremail_case_template_close_automatically_pending',
        'crm_poweremail_case_template_close_automatically_open',
        'crm_poweremail_rule_auto_close_from_pending',
        'crm_poweremail_rule_auto_close_from_open',
    ]
    mh.update_xml_records(xml_path=file, init_record_ids=views)
    trans_load(cursor, '{}/{}/i18n/ca_ES.po'.format(config['addons_path'], module), 'ca_ES')
    trans_load(cursor, '{}/{}/i18n/es_ES.po'.format(config['addons_path'], module), 'es_ES')


def down(cursor, installed_version):
    pass


migrate = up
