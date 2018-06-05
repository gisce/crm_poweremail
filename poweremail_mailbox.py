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

    def update_case_from_mail(
            self, cursor, uid, p_mail_id, case_id, email, context=None):
        """
        Update the case with the data from the poweremail and the email

        1. Description (History)
        2. Log (History)
        3. Addresses (Watchers CC)

        :param cursor:      OpenERP Cursor
        :param uid:         Res.User ID
        :param p_mail_id:   Poweremail.Mailbox ID
        :param case_id:     Crm.Case ID
        :param email:       Qreu.Email instance (related to the mailbox ID)
        :param context:     OpenERP Context
        :return:
        """
        if context is None:
            context = {}
        if isinstance(p_mail_id, (list, tuple)):
            p_mail_id = p_mail_id[0]
        if isinstance(case_id, (list, tuple)):
            case_id = case_id[0]
        p_mail = self.browse(cursor, uid, p_mail_id, context=context)
        case_obj = self.pool.get('crm.case')
        section_obj = self.pool.get('crm.case.section')

        # 1.- Description
        old_descr = case_obj.read(
            cursor, uid, case_id, ['description']
        )['description']
        if old_descr:
            case_obj._history(
                cursor, uid,
                case_obj.browse(cursor, uid, [case_id]),
                _('Reply'), history=True,
                email=email.from_.address
            )
        body_text = quotations.extract_from_plain(p_mail.pem_body_text)
        case_obj.write(cursor, uid, case_id, {
            'description': body_text
        })

        # 2.- Logs
        case_obj._history(
            cursor, uid, case_obj.browse(cursor, uid, [case_id]),
            _('Reply'), history=True, email=email.from_.address
        )

        # 3.- Addresses
        case_data = case_obj.read(
            cursor, uid, case_id, [
                'email_cc', 'section_id'
            ], context=context
        )
        reply_to = section_obj.read(
            cursor, uid, case_data['section_id'][0], ['reply_to']
        )['reply_to']
        # Emails from CC
        emails_from_mail = []
        for address in email.cc:
            if reply_to in address:
                continue
            if address not in case_data['email_cc']:
                emails_from_mail.append(address.strip())
        # Emails from TO
        for address in email.to:
            if reply_to in address:
                continue
            if address not in case_data['email_cc']:
                emails_from_mail.append(address.strip())
        # Email from FROM
        if (
            reply_to not in email.from_.address and
            email.from_.address not in case_data['email_cc']
        ):
            emails_from_mail.append('{} <{}>'.format(
                email.from_.display_name, email.from_.address
            ).strip())
        # Add all addresses to the CC if they are not in there
        emails_from_mail = u','.join(list(set(
            case_data['email_cc'].split(',') + emails_from_mail)))
        case_obj.write(
            cursor, uid, [case_id], {
                'email_cc': emails_from_mail
            }, context=context
        )

    def forward_case_response(
            self, cursor, uid, pmail_id, case, email, context=None):
        """
        Make a forwarding poweremail.mailbox with all the recipients from the
        case, excluding those in the shared email
        :param cursor:      OpenERP Cursor
        :param uid:         OpenERP User ID
        :param pmail_id:    Poweremail.Mailbox ID
        :param case:        Browse Record
        :param email:       Qreu.Email instance
        :param context:     OpenERP Context
        :return:
        """
        case_obj = self.pool.get('crm.case')
        mailbox_obj = self.pool.get('poweremail.mailbox')
        email_from = case.section_id.reply_to
        email_to = case_obj.filter_emails(
            (
                case.get_cc_emails() +
                [case.user_id.address_id.email, case.partner_address_id.email]
            ),
            email.from_.address,
            case,
            todel_emails=email.recipients.addresses+[case.section_id.reply_to]
        )
        email_bcc = case_obj.filter_emails(
            case.get_bcc_emails(),
            email.from_.address,
            case,
            todel_emails=(
                email.recipients.addresses +
                [case.section_id.reply_to] +
                email_to
            )
        )
        if email_to:
            p_mail = self.browse(cursor, uid, pmail_id, context=context)
            vals_forward = {
                'pem_to': email_to[0],
                'pem_from': email_from,
                'pem_cc': ','.join(email_to[1:]) if len(email_to[1:]) else '',
                'pem_bcc': ','.join(email_bcc) if email_bcc else '',
                'pem_subject': p_mail.pem_subject,
                'pem_body_text': p_mail.pem_body_text,
                'pem_body_html': p_mail.pem_body_html,
                'pem_folder': 'outbox',
                'pem_account_id': p_mail.pem_account_id.id,
                'mail_type': 'multipart/alternative',
                'date_mail': datetime.now().strftime('%Y-%m-%d'),
                'pem_message_id': p_mail.pem_message_id,
                'conversation_id': case.conversation_id.id,
            }
            mailbox_obj.create(cursor, uid, vals_forward, context=context)
        elif email_bcc:
            p_mail = self.browse(cursor, uid, pmail_id, context=context)
            for bcc in email_bcc:
                vals_forward = {
                    'pem_to': bcc,
                    'pem_from': email_from,
                    'pem_subject': p_mail.pem_subject,
                    'pem_body_text': p_mail.pem_body_text,
                    'pem_body_html': p_mail.pem_body_html,
                    'pem_folder': 'outbox',
                    'pem_account_id': p_mail.pem_account_id.id,
                    'mail_type': 'multipart/alternative',
                    'date_mail': datetime.now().strftime('%Y-%m-%d'),
                    'pem_message_id': p_mail.pem_message_id,
                    'conversation_id': case.conversation_id.id,
                }
                mailbox_obj.create(cursor, uid, vals_forward, context=context)

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
                body_text = quotations.extract_from_plain(p_mail.pem_body_text)
                case = self.create_crm_case(
                    cursor, uid, p_mail.id, section_id, body_text=body_text
                )
            else:
                self.update_case_from_mail(
                    cursor, uid, p_mail.id, case_id, mail, context=context
                )
                case = case_obj.browse(cursor, uid, case_id[0], context=context)
                self.forward_case_response(
                    cursor, uid, p_mail.id, case, mail, context=context
                )

        return res_id


PoweremailMailboxCRM()
