# -*- coding: utf-8 -*-
from __future__ import absolute_import

from oopgrade.oopgrade import MigrationHelper
from tools import config


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    module = 'crm_poweremail'
    mh = MigrationHelper(cursor, module)

    mh.update_xml_records(
        xml_path='crm_view.xml',
        init_record_ids=['crm_case-view'],
    )


def down(cursor, installed_version):
    pass


migrate = up
