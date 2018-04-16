# coding=utf-8
from __future__ import unicode_literals
from dateutil.relativedelta import relativedelta
from datetime import datetime

from destral import testing
from destral.transaction import Transaction
from expects import *

import logging


class TestCRMPoweremail(testing.OOTestCase):
    def setUp(self):
        self.txn = Transaction().start(self.database)
        self.logger = logging.getLogger(__name__)
        self.cursor = self.txn.cursor
        self.uid = self.txn.user
        self.pool = self.txn.pool

    def tearDown(self):
        self.txn.stop()

    def test_onchange_address_ids(self):
        # def _onchange_address_ids(
        # cursor, uid, ids,addr_type=False, addr_ids=False,context=None
        imod_obj = self.pool.get('ir.model.data')
        case_obj = self.pool.get('crm.case')
        case_id = imod_obj.get_object_reference(
            self.cursor, self.uid, 'crm_poweremail', 'crmpoweremail_case01')[1]
        case = case_obj.browse(self.cursor, self.uid, case_id)
        self.assertEqual(case.email_cc, 'test2@mail.com, me@example.com')
        self.assertEqual(case.email_bcc, 'test@mail.com, test@example.com')
        appended_string = 'testing@example.com, test2@mail.com, me@example.com'
        not_appended_string = 'test2@mail.com, me@example.com'
        self.assertEqual(
            case._onchange_address_ids('cc', [[1, 1, [1]]]), {
                'value': {
                    'email_cc': appended_string
                }
            },
            msg='Appended string does not match with the new address'
        )
        case.write({'email_cc': appended_string})
        self.assertEqual(
            case._onchange_address_ids('cc', [[1, 1, []]]), {
                'value': {
                    'email_cc': not_appended_string
                }
            },
            msg='Removing address does not return correct string'
        )
