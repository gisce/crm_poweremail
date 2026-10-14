# -*- coding: utf-8 -*-
from __future__ import absolute_import
from destral import testing
from destral.patch import PatchNewCursors
from signals import DB_CURSOR_COMMIT


class TestCrmActionCase(testing.OOTestCaseWithCursor):

    def setUp(self):
        super(TestCrmActionCase, self).setUp()
        self.pool = self.openerp.pool
        self.context = self.txn.context

    def tearDown(self):
        super(TestCrmActionCase, self).tearDown()

    @PatchNewCursors()
    def test_crm_case_reopen_case_when_email_arrives(self):
        cursor, uid, context = self.cursor, self.uid, self.context
        case_obj = self.pool.get('crm.case')
        section_obj = self.pool.get('crm.case.section')
        rule_obj = self.pool.get('crm.case.rule')
        mailbox_obj = self.pool.get('poweremail.mailbox')
        imd_obj = self.pool.get('ir.model.data')

        acc_id = imd_obj.get_object_reference(
            cursor, uid, 'poweremail', 'info_energia_from_email'
        )[1]
        ctx = context.copy()

        section_id = section_obj.create(cursor, uid, {
            'name': 'Test Section',
            'reply_to': 'section@example.com',
        }, context=ctx)

        case_id = case_obj.create(cursor, uid, {
            'name': 'Test Case',
            'section_id': section_id,
            'state': 'done',
        }, context=ctx)
        case = case_obj.simple_browse(cursor, uid, case_id, context=ctx)

        rule_obj.create(cursor, uid, {
            'name': 'Test Rule Open Case From Email',
            'trg_email': True,
            'trg_state_from': 'done',
            'act_state': 'open',
        }, context=ctx)

        mail_source = ('S:')
        DB_CURSOR_COMMIT.send(cursor)

        mailbox_obj.create(cursor, uid, {
            'pem_body_text': 'Closed case reply',
            'pem_mail_orig': mail_source,
            'pem_account_id': acc_id,
            'conversation_id': case.conversation_id.id,
        }, context=ctx)
        DB_CURSOR_COMMIT.send(cursor)

        case = case_obj.simple_browse(cursor, uid, case_id, context=ctx)
        self.assertEqual(case.state, 'open')
