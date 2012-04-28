# -*- coding: utf-8 -*-
from tools import email_send

old_email_send = email_send

def poweremail_email_send(email_from, email_to, subject, body, email_cc=None,
                          email_bcc=None, reply_to=False, attach=None,
                          tinycrm=False, ssl=False, debug=False,
                          subtype='plain', x_headers=None):
    """Monkepatching OpenERP email_send function with poweremail.
    """
    if not tinycrm:
        old_email_send(email_from, email_to, subject, body, email_cc, email_bcc,
                       reply_to, attach, tinycrm, ssl, debug, subtype,
                       x_headers)
    else:
        mailbox_values = {
            'pem_from': email_from,
            'pem_to': email_to,
            'pem_cc': email_cc,
            'pem_bcc': email_bcc,
            'pem_subject': subject,
            'pem_account_id' : False,
            'state':'na',
            'folder':'outbox',
            'mail_type':'multipart/alternative'
        }
        if '<html>' in body:
            body = body.replace('\n', '<br />')
            mailbox_values['pem_body_text'] = ''
            mailbox_values['pem_body_html'] = body
        else:
            mailbox_values['pem_body_text'] = body
            mailbox_values['pem_body_html'] = ''

# Monkeypatch for the win
email_send = poweremail_email_send