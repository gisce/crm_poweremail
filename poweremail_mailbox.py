# -*- coding: utf-8 -*-
from osv import osv
from tools.translate import _
from talon import quotations

import qreu


class PoweremailMailboxCRM(osv.osv):
    """Overwriting create.
    """
    _name = 'poweremail.mailbox'
    _inherit = 'poweremail.mailbox'

    def get_partner_address(self, cursor, uid, p_mail_id):
        """
        Gets or Creates the 'res.partner.address' from a poweremail_mailbox
        :param cursor:      OpenERP Cursor
        :param uid:         OpenERP User ID
        :param p_mail_id:   PowerEmail Mailbox object ID
        :return:            Res.Partner.Address (browsed)
        """
        address_obj = self.pool.get('res.partner.address')
        partner_obj = self.pool.get('res.partner')
        p_mail = self.pool.get('poweremail.mailbox').read(
            cursor, uid, p_mail_id, ['pem_mail_orig', 'pem_from']
        )
        mail = qreu.Email(p_mail['pem_mail_orig'])
        try:
            address_id = address_obj.search(cursor, uid, [
                ('email', '=', qreu.address.parse(p_mail['pem_from']).address)
            ])
        except Exception as err:
            import logging
            logging.getLogger('poweremail.mailbox').error(
                _('Could not parse poweremail_mailbox '
                  'pem_from address with qreu')
            )
            return False
        if not address_id:
            # If not found: create partner address
            address_email = mail.from_.address
            address_name = mail.from_.display_name or address_email
            address = address_obj.create(cursor, uid, {
                'name': address_name,
                'email': address_email
            })
            address_id = address.id
            domain = address_email.split('@')[-1]
            partner_id = partner_obj.search(
                cursor, uid, [
                    ('domain', '=', domain)
                ]
            )
            if partner_id:
                address_obj.write(
                    cursor, uid, address_id, {'partner_id': partner_id}
                )
        return address_obj.browse(cursor, uid, address_id)

    def create_crm_case(self, cursor, uid, p_mail_id, section_id,
                        body_text=False, context=None):
        """
        Creates a CRM.case object from a poweremail.mailbox object
        :param cursor:      OpenERP Cursor
        :param uid:         OpenERP User ID
        :param p_mail_id:   PowerEmail Mailbox object
        :param section_id:  CRM.case.section that the new case must belong
        :param body_text:   Mail body parsed, used in the CRM.case.description
        :param context:     OpenERP Context, passed to the create method
        :return:
        """
        if context is None:
            context = {}
        case_obj = self.pool.get('crm.case')
        section_obj = self.pool.get('crm.case.section')
        poweremail_obj = self.pool.get('poweremail.mailbox')

        p_mail = poweremail_obj.read(cursor, uid, p_mail_id, [
            'conversation_id', 'pem_subject', 'pem_from', 'pem_cc'
        ])
        section = section_obj.read(cursor, uid, section_id, ['user_id'])

        case_vals = {
            'conversation_id': p_mail['conversation_id'][0],
            'name': p_mail['pem_subject'],
            'section_id': section['id'],
            'description': body_text,
            'email_from': p_mail['pem_from'],
            'email_cc': p_mail['pem_cc'],
            'user_id': section['user_id'][0],
        }
        address = self.get_partner_address(
            cursor, uid, p_mail['id']
        )
        if address:
            case_vals.update({
                'partner_address_id': address.id,
                'partner_id': address.partner_id
            })
        return case_obj.create(cursor, uid, case_vals, context)

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
            # Re-browse to get the content
            p_mail = self.browse(cursor, uid, res_id, context=context)
            body_text = quotations.extract_from_plain(p_mail.pem_body_text)
            section_id = section_id[0]
            section = section_obj.browse(cursor, uid, section_id)
            case_id = case_obj.search(cursor, uid, [
                ('conversation_id', '=', p_mail.conversation_id.id)
            ])
            # If forwarding case e-mail, just send the e-mail
            if mail.from_.address == section.reply_to:
                cases = case_obj.browse(cursor, uid, case_id)
                case_obj._history(
                    cursor, uid, cases, _('Forward'), history=False,
                    email=mail.from_.address
                )
                return res_id
            if not case_id:
                # If not found a conversation, add new case with email values
                add_obj = self.pool.get('res.partner.address')
                addr_id = add_obj.search(cursor, uid, [
                    ('email', '=', qreu.address.parse(p_mail.pem_from).address)
                ])
                section = section_obj.browse(cursor, uid, section_id)
                case_vals = {
                    'conversation_id': p_mail.conversation_id.id,
                    'name': p_mail.pem_subject,
                    'section_id': section_id,
                    'description': body_text,
                    'email_from': p_mail.pem_from,
                    'email_cc': p_mail.pem_cc,
                    'user_id': section.user_id and section.user_id.id,
                }
                if addr_id:
                    # If partner address found get address and partner id
                    address = add_obj.read(
                        cursor, uid, addr_id[0], ['partner_id']
                    )
                    address_id = addr_id[0]
                    partner_id = address['partner_id'][0]
                else:
                    partner_obj = self.pool.get('res.partner')
                    address_email = mail.from_.address
                    address_name = mail.from_.display_name or address_email
                    new_address = add_obj.create(cursor, uid, {
                        'name': address_name,
                        'email': address_email
                    })
                    address_id = new_address.id
                    domain = address_email.split('@')[-1]
                    partner_id = partner_obj.search(
                        cursor, uid, [
                            ('domain', '=', domain)
                        ]
                    )
                    if partner_id:
                        add_obj.write(
                            cursor, uid, address_id, {'partner_id': partner_id}
                        )
                    else:
                        partner_id = False

                case_vals.update({
                    'partner_address_id': address_id,
                    'partner_id': partner_id
                })
                case_obj.create(cursor, uid, case_vals)
            else:
                case_id = case_id[0]
                old_descr = case_obj.read(
                    cursor, uid, case_id, ['description']
                )['description']
                if old_descr:
                    cases = case_obj.browse(cursor, uid, [case_id])
                    case_obj._history(
                        cursor, uid, cases, _('Reply'), history=True,
                        email=mail.from_.address
                    )
                case_obj.write(cursor, uid, case_id, {
                    'description': body_text
                })
                cases = case_obj.browse(cursor, uid, [case_id])
                case_obj._history(
                    cursor, uid, cases, _('Reply'), history=True,
                    email=mail.from_.address
                )

        return res_id
 
PoweremailMailboxCRM()
