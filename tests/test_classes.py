# -*- coding: utf-8 -*-
from __future__ import absolute_import
from osv import osv, fields


class GiscedataCrmInheritsTest(osv.OsvInherits):

    _name = "giscedata.crm.inherits.test"
    _test_class = True
    _inherits = {"crm.case": "crm_id"}
    _order = 'id desc'

    _columns = {
        'crm_id': fields.many2one('crm.case', required=True),
    }

    def apply_crm_rules(
            self, cursor, uid, ids, state_to='done', context=None):
        cases = [(record_id, state_to) for record_id in ids]
        self.write(
            cursor, uid, ids, {'state': state_to}, context=context
        )
        return self.pool.get('crm.case')._run_rules(
            cursor, uid, self, cases, state_to, context=context
        )


GiscedataCrmInheritsTest()
