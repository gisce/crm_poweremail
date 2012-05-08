# -*- coding: utf-8 -*-
from osv import osv

class PoweremailMailboxCRM(osv.osv):
    """Overwriting create.
    """
    _name = 'poweremail.mailbox'
    _inherit = 'poweremail.mailbox'

    def create(self, cursor, uid, vals, context=None):
        """If some crm section reply_to has this pem_account create a CRM Case.
        """
        res_id = super(PoweremailMailboxCRM, self).create(cursor, uid, vals,
                                                          context)
        p_mail = self.browse(cursor, uid, res_id)
        case_obj = self.pool.get('crm.case')
        section_obj = self.pool.get('crm.case.section')
        account_obj = self.pool.get('poweremail.core_accounts')
        pem_account = account_obj.browse(cursor, uid, vals['pem_account_id'])
        search_params = [('reply_to', '=', p_mail.pem_account_id.email_id)]
        section_id = section_obj.search(cursor, uid, search_params)
        if section_id:
            section_id = section_id[0]
            case_id = case_obj.search(cursor, uid, [
                ('conversation_id', '=', p_mail.conversation_id.id)
            ])
            if not case_id:
                add_obj = self.pool.get('res.partner.address')
                addr_id = add_obj.search(cursor, uid, [
                    ('email', '=', p_mail.pem_from)
                ])
                section = section_obj.browse(cursor, uid, section_id)
                case_vals = {
                    'conversation_id': p_mail.conversation_id.id,
                    'name': p_mail.pem_subject,
                    'section_id': section_id,
                    'description': p_mail.pem_body_text,
                    'email_from': p_mail.pem_from,
                    'email_cc': p_mail.pem_cc,
                    'user_id': section.user_id and section.user_id.id,
                }
                if addr_id:
                    address = add_obj.browse(cursor, uid, addr_id[0])
                    case_vals.update({
                        'partner_address_id': address.id,
                        'partner_id': address.partner_id.id
                    })
                case_obj.create(cursor, uid, case_vals)
        return res_id
 
PoweremailMailboxCRM()