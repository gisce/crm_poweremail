# -*- coding: utf-8 -*-
from datetime import datetime
from email.utils import make_msgid

from osv import osv, fields

class CrmCase(osv.osv):
    """Adding poweremail features.
    """
    _name = 'crm.case'
    _inherit = 'crm.case'

    def create(self, cursor, uid, vals, context=None):
        """Overwrite create method to create conversation if not in vals.
        """
        res_id = super(CrmCase, self).create(cursor, uid, vals, context)
        upd  = {'name': vals['name']}
        if 'conversation_id' not in vals:
            conv_obj = self.pool.get('poweremail.conversation')
            conv_id = conv_obj.create(cursor, uid,
                {'name': '[%s] %s' % (res_id, vals['name'])}
            )
            upd['conversation_id'] = conv_id
        self.write(cursor, uid, [res_id], upd)
        return res_id

    def write(self, cursor, uid, ids, vals, context=None):
        """Updates conversation name if crm case name changes.
        """
        if 'name' in vals:
            conv_ids = []
            for crm in self.browse(cursor, uid, ids, context):
                if crm.conversation_id:
                    crm.conversation_id.write(
                        {'name': '[%s] %s' % (crm.id, vals['name'])}
                    )
        res = super(CrmCase, self).write(cursor, uid, ids, vals, context)
        return res

    def email_send(self, cursor, uid, case, emails, body, context=None):
        """Using poweremail to send mails.
        """
        pm_account_obj = self.pool.get('poweremail.core_accounts')
        pm_mailbox_obj = self.pool.get('poweremail.mailbox')
        body = self.format_mail(case, body)
        if (case.user_id and case.user_id.address_id
                and case.user_id.address_id.email):
            emailfrom = case.user_id.address_id.email
        else:
            emailfrom = case.section_id.reply_to
        reply_to = case.section_id.reply_to or False
        if reply_to: reply_to = reply_to.encode('utf8')
        if not emailfrom:
            raise osv.except_osv(_('Error!'),
                    _("No E-Mail ID Found for your Company address or missing "
                      "reply address in section!"))
        pem_account_id = pm_account_obj.search(cursor, uid, [
            ('email_id', '=', case.section_id.reply_to)
        ])
        if not pem_account_id:
            raise osv.except_osv(_('Error!'),
                    _("No E-Mail ID Found in Power Email for this section or "
                      "missing reply address in section."))
        # TODO: Improve reply-to finding in conversation
        pm_mailbox_obj.create(cursor, uid, {
            'pem_from': emailfrom,
            'pem_to': ', '.join(set(emails)),
            'pem_subject': '[%d] %s' % (case.id, case.name.encode('utf8')),
            'pem_body_text': body,
            'pem_account_id': pem_account_id[0],
            'folder': 'outbox',
            'date_mail': datetime.now().strftime('%Y-%m-%d'),
            'pem_message_id': make_msgid('tinycrm-%s' % case.id),
            'conversation_id': case.conversation_id.id
        })
        return True

    def _conversation_mails(self, cursor, uid, ids, field_name, args,
                            context=None):
        """Returns all the mails from this conversation (case).
        """
        res = {}
        conv_obj = self.pool.get('poweremail.conversation')
        for case in self.browse(cursor, uid, ids, context):
            if not case.conversation_id:
                res[case.id] = []
            else:
                res[case.id] = [x.id for x in case.conversation_id.mails]
        return res
    
    _columns = {
        'conversation_id': fields.many2one(
            'poweremail.conversation',
            'Conversation',
             ondelete='restrict'
        ),
        'conversation_mails': fields.function(
            _conversation_mails,
            type='one2many',
            obj='poweremail.mailbox',
            method=True
        )
    }

CrmCase()