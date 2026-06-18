# -*- coding: utf-8 -*-
from __future__ import absolute_import

import base64
import mimetypes
import os
import re

from email import encoders
from email.mime.base import MIMEBase
from poweremail.poweremail_core import poweremail_core_accounts
from qreu import Email
from qreu.address import Address, parseaddr
import netsvc
import tools

from tools.translate import _

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO


INLINE_IMAGE_RE = re.compile(
    r'(<img\b[^>]*\bsrc=["\'])attachment://(\d+)(["\'][^>]*>)',
    re.IGNORECASE | re.UNICODE
)


class PoweremailCoreAccountsCRM(poweremail_core_accounts):
    _name = 'poweremail.core_accounts'
    _inherit = 'poweremail.core_accounts'

    def _mailbox_inline_attachment_ids(self, cursor, uid, body_html,
                                       mailbox_id, context=None):
        if not body_html or not mailbox_id:
            return []

        attachment_ids = [
            int(match[1]) for match in INLINE_IMAGE_RE.findall(body_html)
        ]
        if not attachment_ids:
            return []

        mailbox = self.pool.get('poweremail.mailbox').browse(
            cursor, uid, mailbox_id, context=context
        )
        mailbox_attachment_ids = [
            attachment.id for attachment in mailbox.pem_attachments_ids
        ]
        return [
            attachment_id for attachment_id in attachment_ids
            if attachment_id in mailbox_attachment_ids
        ]

    def _inline_content_id(self, attachment):
        return 'poweremail-attachment-{0}@local'.format(attachment.id)

    def _replace_inline_attachment_sources(self, body_html, inline_ids):
        inline_ids = set(inline_ids)
        if not body_html or not inline_ids:
            return body_html

        def replace(match):
            attachment_id = int(match.group(2))
            if attachment_id not in inline_ids:
                return match.group(0)
            return '{0}cid:{1}{2}'.format(
                match.group(1),
                'poweremail-attachment-{0}@local'.format(attachment_id),
                match.group(3)
            )

        return INLINE_IMAGE_RE.sub(replace, body_html)

    def _attachment_filename(self, attachment):
        return (attachment.datas_fname or attachment.name).replace('/', '-')

    def _add_inline_attachment(self, mail, attachment):
        filename = self._attachment_filename(attachment)
        content = base64.b64decode(attachment.datas)
        filetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        maintype, subtype = filetype.split('/', 1)
        part = MIMEBase(maintype, subtype)
        part.set_payload(content)
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            'inline; filename="{0}"'.format(
                mail.remove_accent(u'{0}'.format(os.path.basename(filename)))
            )
        )
        part.add_header(
            'Content-ID',
            '<{0}>'.format(self._inline_content_id(attachment))
        )
        mail.email.attach(part)

    def _add_regular_attachment(self, mail, attachment):
        attachment_buffer = BytesIO()
        attachment_buffer.write(base64.b64decode(attachment.datas))
        mail.add_attachment(
            input_buff=attachment_buffer,
            attname=self._attachment_filename(attachment)
        )

    def _parse_body_html(self, pem_body_html, pem_body_text):
        html = pem_body_text if not pem_body_html else pem_body_html
        if (
                html and html.strip()[0] != '<' and
                '<br/>' not in html and '<br>' not in html
        ):
            html = html.replace('\n', '<br/>')
        return html

    def _parse_sender(self, pem_account, pem_addresses):
        from_addr = pem_addresses.get('FROM', False)
        sender_addr = pem_account
        if from_addr:
            from_addr = Address(*parseaddr(from_addr))
            account_addr = Address(*parseaddr(pem_account))
            if from_addr.display_name:
                sender_addr = u'{} <{}>'.format(
                    from_addr.display_name,
                    account_addr.address
                ).strip()
            if from_addr.address != account_addr.address:
                if not pem_addresses.get('BCC', False):
                    pem_addresses['BCC'] = []
                pem_addresses['BCC'].append(u'{}'.format(from_addr.address))
                pem_addresses['BCC'] = list(set(pem_addresses['BCC']))
        return sender_addr

    def _send_mail_with_inline_attachments(
            self, cr, uid, ids, addresses, subject='', body=None,
            context=None):
        if body is None:
            body = {}
        if context is None:
            context = {}

        logger = netsvc.Logger()
        try:
            addresses_list = self.get_ids_from_dict(addresses)
        except Exception as error:
            logger.notifyChannel(
                _('Power Email'), netsvc.LOG_ERROR,
                _('Cannot send mails of accounts {} '
                  'when the addresses list is empty').format(ids)
            )
            return error

        subject = subject or context.get('subject', '') or ''
        body_html = self._parse_body_html(
            pem_body_html=tools.ustr(body.get('html', '')),
            pem_body_text=tools.ustr(body.get('text', ''))
        )
        mailbox_id = context.get('poweremail_id')
        inline_ids = self._mailbox_inline_attachment_ids(
            cr, uid, body_html, mailbox_id, context=context
        )
        body_html = self._replace_inline_attachment_sources(
            body_html, inline_ids
        )
        inline_ids = set(inline_ids)
        extra_headers = context.get('headers', {})

        mailbox = self.pool.get('poweremail.mailbox').browse(
            cr, uid, mailbox_id, context=context
        )
        for account_id in ids:
            account = self.browse(cr, uid, account_id, context)
            sender_name = '{} <{}>'.format(account.name, account.email_id)
            sender_name = self._parse_sender(
                pem_account=sender_name,
                pem_addresses=addresses_list
            )
            if account.user.company_id:
                extra_headers.update({
                    'Organitzation': account.user.company_id.name
                })
            elif 'Organitzation' in extra_headers:
                extra_headers.pop('Organitzation')

            with self.get_sender(account):
                mail = Email(**{
                    'subject': subject,
                    'from': sender_name,
                    'to': addresses_list.get('To', []),
                    'cc': addresses_list.get('CC', []),
                    'bcc': addresses_list.get('BCC', []),
                    'body_text': tools.ustr(body.get('text', '')),
                    'body_html': body_html
                })
                mail.email.set_type('multipart/related')
                for header, value in extra_headers.items():
                    mail.add_header(header, value)
                for attachment in mailbox.pem_attachments_ids:
                    if attachment.id in inline_ids:
                        self._add_inline_attachment(mail, attachment)
                    else:
                        self._add_regular_attachment(mail, attachment)
                try:
                    return mail.send()
                except Exception as error:
                    logger.notifyChannel(
                        _('Power Email'), netsvc.LOG_ERROR,
                        _('Sending mail from Account {} failed.\n'
                          'Description: {}').format(account_id, error)
                    )
                    continue

    def send_mail(self, cr, uid, ids, addresses, subject='', body=None,
                  payload=None, context=None):
        if context is None:
            context = {}
        body_html = body and tools.ustr(body.get('html', '')) or ''
        inline_ids = self._mailbox_inline_attachment_ids(
            cr, uid, body_html, context.get('poweremail_id'), context=context
        )
        if not inline_ids:
            return super(PoweremailCoreAccountsCRM, self).send_mail(
                cr, uid, ids, addresses, subject=subject, body=body,
                payload=payload, context=context
            )
        return self._send_mail_with_inline_attachments(
            cr, uid, ids, addresses, subject=subject, body=body,
            context=context
        )


PoweremailCoreAccountsCRM()
