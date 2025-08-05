# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function
from destral import testing
from destral.transaction import Transaction
from qreu import Email
from addons import get_module_resource
from html2text import html2text

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


class TestCrmPoweremailWithEmails(testing.OOTestCaseWithCursor):
    def setUp(self):
        super(TestCrmPoweremailWithEmails, self).setUp()
        # Create section with reply-to email
        self.section_id = self.openerp.pool.get('crm.case.section').create(
            self.cursor, self.uid, {
                'name': 'Test Section',
                'reply_to': 'sac@example.com'
            })
        # Create account id
        acc_obj = self.openerp.pool.get('poweremail.core_accounts')
        vals = {
            'name': 'Test account',
            'user': self.uid,
            'email_id': 'test2@example.com',
            'smtpserver': 'smtp.example.com',
            'smtpport': 587,
            'smtpuname': 'test',
            'smtppass': 'test',
            'company': 'yes'
        }
        self.pem_account_id = acc_obj.create(self.cursor, self.uid, vals)

    def create_email_case(self, raw_email, account_id=None):
        if account_id is None:
            account_id = self.pem_account_id
        parsed = Email.parse(raw_email)

        def get_payloads(parsed_mail):
            """
            Parse the Email with qreu's Email and return a dict with:
            - 'text': body_text
            - 'html': body_html
            - 'attachments': [attachments]
            """
            parts = parsed_mail.body_parts
            attachments = [
                (v['type'], v['name'], v['content'])
                for v in parsed_mail.attachments
            ]
            body_text = parts.get('plain', '')
            if not body_text:
                body_text = html2text(parts.get('html', ''))
            return {
                'text': body_text,
                'html': parts.get('html', ''),
                'attachments': attachments,
            }
        parsed_mail = get_payloads(self, parsed)
        vals = {
            'pem_from': parsed.from_.address,
            'pem_to': ','.join(parsed.to),
            'pem_cc': ','.join(parsed.cc),
            'pem_bcc': ','.join(parsed.bcc),
            'pem_recd': parsed.email['date'],
            'date_mail': parsed.email['date'],
            'pem_subject': parsed.subject,
            'folder': 'inbox',
            'state': 'na',
            'pem_body_text': parsed_mail['text'],
            'pem_body_html': parsed_mail['html'],
            'pem_account_id': account_id,
            'pem_message_id': parsed.email['Message-ID'].strip(),
            'pem_mail_orig': raw_email
        }
        pem_obj = self.openerp.pool.get('poweremail.mailbox')
        email_id = pem_obj.create(self.cursor, self.uid, vals)
        return email_id

    def test_create_email_case(self):
        case_obj = self.openerp.pool.get('crm.case')
        pem_obj = self.openerp.pool.get('poweremail.mailbox')
        with open(get_module_resource('crm_poweremail', 'tests', 'fixtures', 'mail.txt'), 'rb') as f:
            raw_email = f.read()
        email_id = self.create_email_case(raw_email)
        # It should be a case related to the email
        email = pem_obj.browse(self.cursor, self.uid, email_id)
        case_ids = case_obj.search(self.cursor, self.uid, [
            ('conversation_id', '=', email.conversation_id.id)
        ])
        self.assertEqual(len(case_ids), 1)
        case = case_obj.browse(self.cursor, self.uid, case_ids[0])
        self.assertEqual(case.name, email.pem_subject)
        self.assertEqual(case.email_from, email.pem_from)
        self.assertEqual(case.description, email.pem_body_text)
        self.assertEqual(case.email_cc, email.pem_cc)
