# -*- coding: utf-8 -*-
from __future__ import absolute_import

from destral.patch import PatchNewCursors
from destral.testing import OOTestCaseWithCursor
from oorq.oorq import AsyncMode


class TestAtcCrmRuleEmail(OOTestCaseWithCursor):

    def setUp(self):
        super(TestAtcCrmRuleEmail, self).setUp()
        self.context = self.txn.context
        self.pool = self.openerp.pool
        self.atc_obj = self.pool.get('giscedata.atc')
        self.crm_obj = self.pool.get('crm.case')
        self.rule_obj = self.pool.get('crm.case.rule')
        self.template_obj = self.pool.get('poweremail.templates')
        self.mailbox_obj = self.pool.get('poweremail.mailbox')
        self.log_obj = self.pool.get('crm.case.log')

        address_obj = self.pool.get('res.partner.address')
        user_obj = self.pool.get('res.users')
        user = user_obj.simple_browse(
            self.cursor, self.uid, self.uid, context=self.context
        )
        if not user.address_id:
            address_id = address_obj.create(
                self.cursor, self.uid, {
                    'name': 'CRM rule test user',
                    'email': 'agent@example.com',
                }, context=self.context
            )
            user_obj.write(
                self.cursor, self.uid, [self.uid],
                {'address_id': address_id}, context=self.context
            )

        section_obj = self.pool.get('crm.case.section')
        self.section_id = section_obj.create(
            self.cursor, self.uid, {
                'name': 'ATC PowerEmail rules test',
                'reply_to': 'atc-rules@example.com',
            }, context=self.context
        )
        account_obj = self.pool.get('poweremail.core_accounts')
        self.account_id = account_obj.create(
            self.cursor, self.uid, {
                'name': 'ATC PowerEmail rules test',
                'email_id': 'atc-rules@example.com',
                'user': self.uid,
                'company': 'yes',
                'smtpserver': 'localhost',
                'smtpport': 25,
            }, context=self.context
        )

    def _create_atc_with_distinct_crm_id(self):
        values = {
            'name': 'ATC PowerEmail rule case',
            'section_id': self.section_id,
            'state': 'draft',
        }
        atc_id = self.atc_obj.create(
            self.cursor, self.uid, values, context=self.context
        )
        crm_id = self.atc_obj.read(
            self.cursor, self.uid, atc_id, ['crm_id'], context=self.context
        )['crm_id'][0]
        if atc_id == crm_id:
            self.crm_obj.create(
                self.cursor, self.uid, {
                    'name': 'CRM sequence offset',
                    'section_id': self.section_id,
                    'state': 'draft',
                }, context=self.context
            )
            atc_id = self.atc_obj.create(
                self.cursor, self.uid, values, context=self.context
            )
            crm_id = self.atc_obj.read(
                self.cursor, self.uid, atc_id, ['crm_id'],
                context=self.context
            )['crm_id'][0]
        self.assertNotEqual(atc_id, crm_id)
        return atc_id, crm_id

    def _create_template_and_rule(
            self, model_name, subject, state_from):
        model_ids = self.pool.get('ir.model').search(
            self.cursor, self.uid, [('model', '=', model_name)], limit=1,
            context=self.context
        )
        self.assertEqual(len(model_ids), 1)
        template_id = self.template_obj.create(
            self.cursor, self.uid, {
                'name': 'CRM rule template {}'.format(model_name),
                'object_name': model_ids[0],
                'def_to': 'recipient@example.com',
                'def_subject': subject,
                'def_body_text': 'Body for ${object.name}',
                'pem_account_id': self.account_id,
            }, context=self.context
        )
        self.rule_obj.create(
            self.cursor, self.uid, {
                'name': 'CRM rule email {}'.format(model_name),
                'trg_section_id': self.section_id,
                'trg_state_from': state_from,
                'trg_state_to': 'done',
                'pm_template_id': template_id,
            }, context=self.context
        )
        return template_id

    def _assert_rule_email(
            self, record_id, crm_id, transition, model_name, subject,
            template_id):
        previous_log_ids = set(self.log_obj.search(
            self.cursor, self.uid, [('name', '=', 'Rule')],
            context=self.context
        ))
        with AsyncMode(mode='sync'), PatchNewCursors():
            transition(
                self.cursor, self.uid, [record_id], context=self.context
            )

        mailbox_ids = self.mailbox_obj.search(
            self.cursor, self.uid, [
                ('reference', '=', '{},{}'.format(model_name, record_id)),
                ('folder', '=', 'outbox'),
            ], context=self.context
        )
        self.assertEqual(len(mailbox_ids), 1)
        mailbox = self.mailbox_obj.read(
            self.cursor, self.uid, mailbox_ids[0], [
                'pem_subject', 'pem_body_text', 'pem_message_id',
                'reference', 'template_id',
            ], context=self.context
        )
        self.assertEqual(mailbox['pem_subject'], subject)
        self.assertEqual(mailbox['template_id'][0], template_id)
        self.assertEqual(
            mailbox['reference'], '{},{}'.format(model_name, record_id)
        )
        self.assertIn('Body for', mailbox['pem_body_text'])
        self.assertIn('tinycrm-{}'.format(crm_id), mailbox['pem_message_id'])

        current_log_ids = set(self.log_obj.search(
            self.cursor, self.uid, [('name', '=', 'Rule')],
            context=self.context
        ))
        rule_log_ids = current_log_ids - previous_log_ids
        self.assertEqual(len(rule_log_ids), 1)
        rule_log = self.log_obj.read(
            self.cursor, self.uid, rule_log_ids.pop(), ['case_id'],
            context=self.context
        )
        self.assertEqual(rule_log['case_id'][0], crm_id)

    def test_atc_rule_email_uses_template_and_functional_reference(self):
        atc_id, crm_id = self._create_atc_with_distinct_crm_id()
        subject = 'ATC {} - ${{object.name}}'.format(atc_id)
        expected_subject = 'ATC {} - ATC PowerEmail rule case'.format(atc_id)
        template_id = self._create_template_and_rule(
            'giscedata.atc', subject, 'done'
        )
        self._assert_rule_email(
            atc_id, crm_id, self.atc_obj.atc_close,
            'giscedata.atc', expected_subject, template_id
        )

    def test_crm_rule_email_keeps_crm_compatibility(self):
        crm_id = self.crm_obj.create(
            self.cursor, self.uid, {
                'name': 'CRM PowerEmail rule case',
                'section_id': self.section_id,
                'state': 'draft',
            }, context=self.context
        )
        subject = 'CRM {} - ${{object.name}}'.format(crm_id)
        expected_subject = 'CRM {} - CRM PowerEmail rule case'.format(crm_id)
        template_id = self._create_template_and_rule(
            'crm.case', subject, 'draft'
        )
        def close_case(cursor, uid, ids, context=None):
            return self.crm_obj.case_close(cursor, uid, ids)

        self._assert_rule_email(
            crm_id, crm_id, close_case,
            'crm.case', expected_subject, template_id
        )
