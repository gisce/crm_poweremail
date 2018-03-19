# -*- coding: utf-8 -*-
from osv import osv
from tools.translate import _
from talon import quotations
from datetime import datetime
from email.utils import make_msgid

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
        :type uid:          int
        :param p_mail_id:   PowerEmail Mailbox object ID
        :type p_mail_id:    int
        :return:            Res.Partner.Address (browsed)
        :rtype:             osv.osv
        """
        address_obj = self.pool.get('res.partner.address')
        partner_obj = self.pool.get('res.partner')
        p_mail = self.pool.get('poweremail.mailbox').read(
            cursor, uid, p_mail_id, ['pem_mail_orig', 'pem_from']
        )
        mail = qreu.Email.parse(p_mail['pem_mail_orig'])
        try:
            address_id = address_obj.search(cursor, uid, [
                ('email', '=', mail.from_.address)
            ])
        except Exception as err:
            import logging
            logging.getLogger('poweremail.mailbox').error(
                _('Could not parse poweremail_mailbox '
                  'pem_from address with qreu')
            )
            return False
        if address_id:
            address_id = address_id[0]
        else:
            # If not found: create partner address
            address_email = mail.from_.address
            address_name = mail.from_.display_name or address_email
            address_id = address_obj.create(cursor, uid, {
                'name': address_name,
                'email': address_email
            })
            domain = address_email.split('@')[-1].strip()
            partner_id = partner_obj.search(
                cursor, uid, [('domain', '=', domain)]
            )
            if not partner_id:
                partner_id = partner_obj.search(
                    cursor, uid, [
                        '|',
                        ('domain', 'ilike', '%' + domain),
                        ('domain', 'ilike', domain + '%')
                    ]
                )
            if partner_id:
                address_obj.write(
                    cursor, uid, address_id, {'partner_id': partner_id[0]}
                )
        return address_obj.browse(cursor, uid, address_id) or False

    def create_crm_case(self, cursor, uid, p_mail_id, section_id,
                        body_text=False, context=None):
        """
        Creates a CRM.case object from a poweremail.mailbox object
        :param cursor:      OpenERP Cursor
        :param uid:         OpenERP User ID
        :type uid:          int
        :param p_mail_id:   PowerEmail Mailbox object
        :type p_mail_id:    int
        :param section_id:  CRM.case.section that the new case must belong
        :type section_id:   int
        :param body_text:   Mail body parsed, used in the CRM.case.description
        :type body_text:    str
        :param context:     OpenERP Context, passed to the create method
        :type context:      dict
        :return:            New crm.case object (browsed)
        :rtype:             osv.osv
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
            'user_id': section['user_id'][0] if section['user_id'] else False,
        }
        address = self.get_partner_address(
            cursor, uid, p_mail['id']
        )
        if address:
            case_vals.update({
                'partner_address_id': address.id,
                'partner_id': address.partner_id.id
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
        # This does not work due to smtp's fetch returning always //SEEN
        # if p_mail.state == 'read':
        #     # If downloaded a readed e-mail: do nothing
        #     return res_id
        # If original format mail, use it
        if p_mail.pem_mail_orig:
            mail = qreu.Email.parse(p_mail.pem_mail_orig)
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
            if mail.from_.address == section.reply_to:
                # Ignore mails sent FROM this section
                return res_id
            case_id = case_obj.search(cursor, uid, [
                ('conversation_id', '=', p_mail.conversation_id.id)
            ])
            if not case_id:
                # If not found a conversation, add new case with email values
                case = self.create_crm_case(
                    cursor, uid, p_mail.id, section_id, body_text=body_text
                )
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
                # Re-browse after write
                cases = case_obj.browse(cursor, uid, [case_id])
                case_obj._history(
                    cursor, uid, cases, _('Reply'), history=True,
                    email=mail.from_.address
                )
                case = cases[0]
                # After crm.case update,
                # Forward the e-mail to case TO, FROM, CCs or BCCs
                # if not in e-mail recipients
                email_from = section.reply_to
                email_to = []
                if case.email_from not in reply_to:
                    email_to.append(case.email_from)
                if case.partner_address_id.email not in reply_to:
                    email_to.append(case.partner_address_id.email)
                for cc_email in case.email_cc:
                    if cc_email not in reply_to:
                        email_to.append(cc_email)
                if email_to:
                    email_to = list(set(email_to))
                    mailbox_obj = self.pool.get('poweremail.mailbox')
                    vals_forward = {}
                    vals_forward.update({
                        'pem_to': email_to[0],
                        'pem_from': email_from,
                        'pem_cc': email_to[1:] if len(email_to[1:]) else False,
                        'pem_subject': p_mail.pem_subject,
                        'pem_body_text': p_mail.pem_body_text,
                        'pem_body_html': p_mail.pem_body_html,
                        'pem_folder': 'outbox',
                        'pem_account_id': p_mail.pem_account_id.id,
                        'mail_type': 'multipart/alternative',
                        'date_mail': datetime.now().strftime('%Y-%m-%d'),
                        'pem_message_id': make_msgid('tinycrm-%s' % case.id),
                        'conversation_id': case.conversation_id.id,
                    })
                    mailbox_obj.create(cursor, uid, vals_forward)
        return res_id
 
PoweremailMailboxCRM()
