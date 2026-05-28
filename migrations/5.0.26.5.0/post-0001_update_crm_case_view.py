# -*- coding: utf-8 -*-
from __future__ import absolute_import
from oopgrade.oopgrade import MigrationHelper
from tools import config


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    module = 'crm_poweremail'
    mh = MigrationHelper(cursor, module)

    file = 'crm_view.xml'
    views = [
        'crm_case-view',
    ]
    mh.update_xml_records(xml_path=file, init_record_ids=views)


def down(cursor, installed_version):
    pass


migrate = up