# -*- coding: utf-8 -*-
from osv import osv
from tools.translate import _

import qreu


class PoweremailMailboxCRM(osv.osv):
    """Overwriting create.
    """
    _name = 'poweremail.mailbox'
    _inherit = 'poweremail.mailbox'

    def create(self, cursor, uid, vals, context=None):
        """If some crm section reply_to has this pem_account create a CRM Case.
        """
        if context is None:
            context = {}
        res_id = super(PoweremailMailboxCRM, self).create(cursor, uid, vals,
                                                          context)
        p_mail = self.browse(cursor, uid, res_id, context=context)
        # If original format mail, use it
        if p_mail.pem_mail_orig:
            mail = qreu.Email(p_mail.pem_mail_orig)
            reply_to = mail.recipients.addresses
        else:
            # If no mail source found, the mail is being sent
            return res_id
        case_obj = self.pool.get('crm.case')
        section_obj = self.pool.get('crm.case.section')
        search_params = [('reply_to', 'in', reply_to)]
        section_id = section_obj.search(cursor, uid, search_params)
        if section_id:
            # Trying to get mail for new email, fails cause no mail on server
            # p_mail.complete_mail()
            # Fuck re-browse to get the content
            p_mail = self.browse(cursor, uid, res_id, context=context)
            section_id = section_id[0]
            case_id = case_obj.search(cursor, uid, [
                ('conversation_id', '=', p_mail.conversation_id.id)
            ])
            if not case_id:
                add_obj = self.pool.get('res.partner.address')
                addr_id = add_obj.search(cursor, uid, [
                    ('email', '=', qreu.address.parse(p_mail.pem_from).address)
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
            else:
                case_obj.write(cursor, uid, case_id, {
                    'description': p_mail.pem_body_text
                })
                cases = case_obj.browse(cursor, uid, case_id)
                case_obj._history(
                    cursor, uid, cases, _('Reply'), history=True,
                    email=mail.from_.address
                )
        return res_id
 
PoweremailMailboxCRM()
