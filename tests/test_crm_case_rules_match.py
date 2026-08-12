# -*- coding: utf-8 -*-
from __future__ import absolute_import
from destral import testing
import six
if six.PY2:
    from mock import MagicMock
else:
    from unittest.mock import MagicMock


class TestCrmCaseRuleMatch(testing.OOTestCaseWithCursor):

    def setUp(self):
        super(TestCrmCaseRuleMatch, self).setUp()
        self.pool = self.openerp.pool
        self.context = self.txn.context

        self.rule_obj = self.pool.get('crm.case.rule')
        self.case_obj = self.pool.get('crm.case')
        self.section_obj = self.pool.get('crm.case.section')

        self.section_id = self.section_obj.create(self.cursor, self.uid, {
            'name': 'Test Section'
        }, context=self.context)

    def tearDown(self):
        super(TestCrmCaseRuleMatch, self).tearDown()

    def test_crm_case_rule_match_triggered_by_email(self):
        cursor, uid, context = self.cursor, self.uid, self.context

        case_id = self.case_obj.create(cursor, uid, {
            'name': 'Test Case',
            'state': 'draft',
            'section_id': self.section_id,
        }, context=context)

        rule_id = self.rule_obj.create(cursor, uid, {
            'name': 'Test Rule Default',
            'active': True,
            'trg_email': True,
        }, context=context)

        case = self.case_obj.simple_browse(cursor, uid, case_id, context=context)
        ctx = context.copy()
        email = MagicMock()
        ok = self.rule_obj.match(cursor, uid, [rule_id], case, None, context=context)
        self.assertFalse(ok)
        ctx.update({'email': email})
        case = self.case_obj.simple_browse(cursor, uid, case.id, context=context)
        ok = self.rule_obj.match(cursor, uid, [rule_id], case, None, context=ctx)
        self.assertTrue(ok)
