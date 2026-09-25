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


GiscedataCrmInheritsTest()
