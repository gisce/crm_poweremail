# coding=utf-8
from destral import testing
from destral.transaction import Transaction

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

    def _check_onchange(self, emails, case_id, mail_type):
        case_obj = self.pool.get('crm.case')
        case = case_obj.browse(self.cursor, self.uid, case_id)
        case_mails = ''
        if mail_type == 'cc':
            case_mails = case.email_cc
        elif mail_type == 'bcc':
            case_mails = case.email_bcc
        self.assertEqual(case_mails, emails,
                         msg='Case emails:\n'
                             '{}\n'
                             '\tDo not match with expected\n'
                             '{}'.format(case_mails, emails))
        appended_string = (
            u'testing@example.com, {}'.format(emails)
        )
        not_appended_string = emails
        changed_addresses = case._onchange_address_ids(mail_type, [[1, 1, [1]]])
        self.assertEqual(
            changed_addresses['value']['email_{}'.format(mail_type)],
            appended_string,
            msg='Appended string:\n'
                '{}\n'
                '\tDoes not match with the new addresses:\n'
                '{}'.format(
                changed_addresses['value']['email_{}'.format(mail_type)],
                appended_string
            )
        )
        vals = {
            'email_{}'.format(mail_type): appended_string,
            '{}_address_ids'.format(mail_type): [[6, 0, [1]]]
        }
        case.write(vals)
        case = case_obj.browse(self.cursor, self.uid, case_id)
        changed_addresses = case._onchange_address_ids(mail_type, [[1, 1, []]])
        self.assertEqual(
            changed_addresses['value']['email_{}'.format(mail_type)],
            not_appended_string,
            msg='Removing address string:\n'
                '{}\n'
                '\tDoes not match with the new addresses:\n'
                '{}'.format(
                case._onchange_address_ids(mail_type, [[1, 1, []]]),
                not_appended_string
            )
        )

    def test_onchange_address_ids(self):
        # def _onchange_address_ids(
        # cursor, uid, ids,addr_type=False, addr_ids=False,context=None
        imod_obj = self.pool.get('ir.model.data')
        address_obj = self.pool.get('res.partner.address')
        address_obj.write(
            self.cursor, self.uid, 1, {'email': 'testing@example.com'})
        case_id = imod_obj.get_object_reference(
            self.cursor, self.uid, 'crm_poweremail', 'crmpoweremail_case01')[1]
        orig_mails_cc = 'test2@mail.com, me@example.com'
        orig_mails_bcc = 'test@mail.com, test@example.com'
        self.logger.info('Testing onchange for CC')
        self._check_onchange(emails=orig_mails_cc,
                             case_id=case_id,
                             mail_type='cc')
        self.logger.info('Testing onchange for BCC')
        self._check_onchange(emails=orig_mails_bcc,
                             case_id=case_id,
                             mail_type='bcc')
