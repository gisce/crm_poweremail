# -*- coding: utf-8 -*-
from osv import osv, fields


class ResPartnerDomain(osv.osv):
    # Add e-mail domain to res.partner for res.partner.address auto-creation

    _name = 'res.partner'
    _inherit = 'res.partner'

    _columns = {
        'domain': fields.char('Email domain', size=128),
    }

ResPartnerDomain()
