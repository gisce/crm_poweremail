# -*- coding: utf-8 -*-
from __future__ import absolute_import
from oopgrade.oopgrade import MigrationHelper

def up(cursor, installed_version):
    if not installed_version:
        return

    sql = """
        ALTER TABLE crm_case
            ALTER COLUMN email_bcc TYPE varchar(1000);
    """
    cursor.execute(sql)

    return True


def down(cursor, installed_version):
    pass


migrate = up

