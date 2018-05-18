# -*- coding: utf-8 -*-
from datetime import datetime
from email.utils import make_msgid
from mako.template import Template

from osv import osv, fields
from tools.translate import _
from tools import config


class CrmCase(osv.osv):
    """Adding poweremail features.
    """
    _name = 'crm.case'
    _inherit = 'crm.case'

    @staticmethod
    def filter_mails(emails, email_from, case, todel_emails=[]):
        """
        :param emails:
        :type emails:           [str]
        :param email_from:
        :type email_from:       str
        :param email_to:
        :type email_to:         [str]
        :param case:
        :type case:             browse_record
        :param todel_emails:
        :type todel_emails:     [str]
        :return:
        """
        to_del_emails = [email for email in todel_emails if email in emails]
        for email in emails:
            if email == '':                          # Remove EMPTY email
                to_del_emails.append(email)
            elif email == email_from:                # Remove FROM email
                to_del_emails.append(email)
            elif email == case.section_id.reply_to:  # Remove SECTION email
                to_del_emails.append(email)
        return list(set(
            [email for email in emails if email not in to_del_emails]
        ))

    def _onchange_address_ids(
            self, cursor, uid, ids,
            addr_type=False, addr_ids=False,
            context=None):
        """
        Onchange method to update watchers emails list when the many2many is updated
        :param cursor:      OpenERP Cursor
        :param uid:         OpenERP current User ID
        :param ids:         OpenERP current OSV ID
        :param addr_type:   Type of the address updated (CC/BCC)
        :type addr_type:    str
        :param addr_ids:    New address ids (with format: [[6,0,ids]])
        :type addr_ids:     list[tuple[int,int,list[int]]]
        :param context:     OpenERp Context
        :return:            Vals to update
        """
        if context is None:
            context = {}
        if addr_type not in ('cc', 'bcc') or not addr_ids:
            return {}
        if isinstance(ids, list):
            ids = ids[0]
        new_addr_ids = addr_ids[0][2]
        res = {}
        to_update = 'email_{}'.format(addr_type)
        to_read = '{}_address_ids'.format(addr_type)
        # Gather all data (Old emails in csv, old_addr_ids && new_addr_ids)
        old_vals = self.read(cursor, uid, ids, [to_read, to_update])
        old_addr_ids = old_vals[to_read]
        old_emails = [
            m.strip() for m in (old_vals[to_update] or '').split(',')
            if m.strip()
        ]
        addresses_obj = self.pool.get('res.partner.address')
        old_addresses = addresses_obj.read(
            cursor, uid, old_addr_ids, ['email'])
        if old_addresses:
            old_addresses = [m['email'] for m in old_addresses if m['email']]
        new_addresses = addresses_obj.read(
            cursor, uid, new_addr_ids, ['email'])
        if new_addresses:
            new_addresses = [m['email'] for m in new_addresses if m['email']]
        # Check emails to keep (in old_emails but not in old_addresses)
        keep_emails = [m for m in old_emails if m not in old_addresses]
        # ADD All emails from new list and keep_emails without duplicated emails
        new_emails = ', '.join(list(set(
            [m for m in new_addresses] + keep_emails)
        ))
        return {'value': {to_update: new_emails or False}}

    def create(self, cursor, uid, vals, context=None):
        """Overwrite create method to create conversation if not in vals.
        """
        res_id = super(CrmCase, self).create(cursor, uid, vals, context)
        upd = {'name': vals['name']}
        if 'conversation_id' not in vals:
            conv_obj = self.pool.get('poweremail.conversation')
            conv_id = conv_obj.create(
                cursor, uid,
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

    def add_to_watchers(
            self, cursor, uid, case_ids, address_ids, bcc=False, context=None):
        """
        ADD the addresses to the watchers
        :param cursor:      OpenERP Cursor
        :param uid:         OpenERP User ID
        :param case_ids:    CRM.Case IDS to update
        :param address_ids: Res.Partner.Address IDS to ADD
        :param bcc:         If should be added to BCC (True) or CC (False)
        :type bcc:          bool
        :param context:     OpenERP Context
        :return:
        """
        if context is None:
            context = {}
        if not isinstance(case_ids, (tuple, list)):
            case_ids = [case_ids]
        if not isinstance(address_ids, (tuple, list)):
            address_ids = [address_ids]
        case_obj = self.pool.get('crm.case')
        addr_obj = self.pool.get('res.partner.address')
        # Get Field Name according to BCC parameter
        fieldname = '{}_address_ids'.format(
            'bcc' if bcc else 'cc'
        )
        # Filter addresses that have email
        address_ids = [
            aid['id']
            for aid in addr_obj.read(
                cursor, uid, address_ids, ['email'], context=context)
            if aid['email']
        ]
        # Add the addresses to each case in IDS parameter
        for case_id in case_ids:
            case_addrs = case_obj.read(
                cursor, uid, [case_id], [fieldname], context=context
            )[0][fieldname]
            # OpenERP relations with name reads as `(id, name)`
            #   We only want the IDs
            case_addrs = [c[0] for c in case_addrs]
            # One2Many and Many2Many may be updated (written) with "[(6,0,ids)]"
            new_addrs = [(6, 0, case_addrs + address_ids)]

            update_str = self._onchange_address_ids(
                cursor, uid, [case_id],
                addr_type=('bcc' if bcc else 'cc'),
                addr_ids=new_addrs,
                context=context
            )
            vals = {
                fieldname: new_addrs,
            }
            vals.update(update_str['value'])
            case_obj.write(
                cursor, uid, [case_id], vals, context=context
            )

    def autowatch(self, cursor, uid, ids, context=None):
        if context is None:
            context = {}
        bcc = context.get('bcc', False)
        user = self.pool.get('res.users').browse(
            cursor, uid, uid, context=context)
        if not user.address_id:
            raise osv.except_osv(
                _(u'Error!'),
                _(u'You do not have an address!')
            )
        if not user.address_id.email:
            raise osv.except_osv(
                _(u"Error!"),
                _(u"Your address does not have an email!")
            )
        self.add_to_watchers(
            cursor, uid, ids, [user.address_id.id], bcc, context
        )



    def email_send(self, cursor, uid, case, emails, body, context=None):
        """Using poweremail to send mails.
        """
        if not context:
            context = {}
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
        email_cc = context.get('email_cc', [])
        email_bcc = context.get('email_bcc', [])
        emails = self.filter_mails(emails, emailfrom, case)
        email_cc = self.filter_mails(
            email_cc, emailfrom, case, todel_emails=emails)
        email_bcc = self.filter_mails(
            email_bcc, emailfrom, case, todel_emails=list(set(email_cc+emails)))
        pm_mailbox_obj.create(cursor, uid, {
            'pem_from': emailfrom,
            'pem_to': ', '.join(set(emails)),
            'pem_subject': '[%d] %s' % (case.id, case.name.encode('utf8')),
            'pem_body_text': body,
            'pem_account_id': pem_account_id[0],
            'folder': 'outbox',
            'date_mail': datetime.now().strftime('%Y-%m-%d'),
            'pem_message_id': make_msgid('tinycrm-%s' % case.id),
            'conversation_id': case.conversation_id.id,
            'pem_cc': ', '.join(set(email_cc)),
            'pem_bcc': ', '.join(set(email_bcc))
        })
        return True

    def remind_user(self, cursor, uid, ids, context=None, attach=False,
                    destination=True):
        """For now, we can leave this method calling original one
        """
        super(CrmCase, self).remind_user(cursor, uid, ids, context, attach,
                                         destination)

    def case_log_reply(self, cursor, uid, ids, context=None, email=False,
                       *args):
        """Using poweremail.
        """
        if not context:
            context = {}
        cases = self.browse(cursor, uid, ids, context)
        for case in cases:
            if not case.email_from:
                raise osv.except_osv(_('Error!'),
                        _('You must put a Partner eMail to use this action!'))
            if not case.user_id:
                raise osv.except_osv(_('Error!'),
                        _('You must define a responsible user for this case '
                          'in order to use this action!'))
            if not case.description:
                raise osv.except_osv(_('Error!'),
                        _('Can not send mail with empty body,you should have '
                          'description in the body'))
        for case in cases:
            self.write(cursor, uid, [case.id], {
                'som': False,
                'canal_id': False,
            })
            emails = [case.email_from]
            if case.email_cc:
                context['email_cc'] = list(set(
                    [x.strip() for x in case.email_cc.split(',')]
                ))
            body = case.description or ''
            emailfrom = case.user_id.address_id \
                        and case.user_id.address_id.email or False
            if not emailfrom:
                raise osv.except_osv(_('Error!'),
                        _("No E-Mail ID Found for your Company address!"))
            self.email_send(cursor, uid, case, emails, body, context)
        self._history(cursor, uid, cases, _('Send'), history=True, email=False)
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
        ),
        'email_bcc': fields.char('Secret Watchers Emails', size=252),
        'cc_address_ids': fields.many2many(
            obj='res.partner.address', rel='crm_case_watchers_address',
            id1='case_id', id2='address_id', string='Watchers Addresses (CC)'
        ),
        'bcc_address_ids': fields.many2many(
            obj='res.partner.address', rel='crm_case_secret_watchers_address',
            id1='case_id', id2='address_id',
            string='Secret Watchers Addresses (BCC)'
        ),
    }


CrmCase()


class CrmCaseRule(osv.osv):
    """Case rule with Poweremail templates.
    """
    _name = 'crm.case.rule'
    _inherit = 'crm.case.rule'

    _columns = {
        'pm_template_id': fields.many2one(
            'poweremail.templates', 'Poweremail Template', ondelete='restrict')
    }
    
    def get_email_addresses(self, cr, uid, rule_id, case, context):
        if isinstance(rule_id, list):
            rule_id = rule_id[0]
        emails = super(CrmCaseRule, self).get_email_addresses(
            cr, uid, rule_id, case, context)
        action = self.pool.get('crm.case.rule').browse(cr, uid, rule_id)
        if action.pm_template_id:
            if action.pm_template_id.def_to:
                try:
                    template_to = (
                        Template(action.pm_template_id.def_to).render(object=case))
                except:
                    raise osv.except_osv(_('Error!'), _(
                        'Poweremail template "Email TO" has bad formatted address'))
                emails.append(template_to)
            if action.pm_template_id.def_cc:
                try:
                    template_cc = (
                        Template(action.pm_template_id.def_cc).render(object=case))
                except:
                    raise osv.except_osv(_('Error!'), _(
                        'Poweremail template "Email CC" has bad formatted address'))
                context.update({
                    'email_cc': list(set(template_cc.split(',')))
                })
            if action.pm_template_id.def_bcc:
                try:
                    template_bcc = (
                        Template(action.pm_template_id.def_bcc).render(object=case))
                except:
                    raise osv.except_osv(_('Error!'), _(
                        'Poweremail template "Email BCC" has bad formatted address'))
                context.update({
                    'email_bcc': list(set(template_bcc.split(',')))
                })

        return list(set(emails))

    def get_email_body(self, cr, uid, rule_id, case, context=None):
        if not context:
            context = {}
        if isinstance(rule_id, list):
            rule_id = rule_id[0]
        if isinstance(case, list):
            case = case[0]
        action_body = super(CrmCaseRule, self).get_email_body(
            cr, uid, rule_id, case, context)
        action_template = self.read(
            cr, uid, rule_id, ['pm_template_id'])['pm_template_id'][0]
        pm_template_obj = self.pool.get('poweremail.templates')
        pm_template = pm_template_obj.browse(cr, uid, action_template)
        pm_send_wizard_obj = self.pool.get('poweremail.send.wizard')
        ctx = context.copy()
        # Get lang from template
        lang = pm_send_wizard_obj.get_value(
            cr, uid, pm_template, pm_template.lang, context, id=case.id)
        if not lang:
            # Get lang from case.partner_id (source)
            if case.partner_id and case.partner_id.lang:
                lang = case.partner_id.lang
            # Get lang from case.user_id (responsible)
            elif case.user_id and case.user_id.context_lang:
                lang = case.user_id.context_lang
            # Get lang from Context (Server-based)
            elif ctx.get('lang', False):
                lang = ctx.get('lang')
            # Get lang from config file
            else:
                lang = config.get('language', False) or False
        if lang:
            ctx['lang'] = lang
        template_body = pm_template_obj.read(
            cr, uid, action_template, ['def_body_text'], ctx)['def_body_text']
        body = template_body or action_body
        body_mako_tpl = Template(body, input_encoding='utf-8')
        rendered_body = body_mako_tpl.render(
            object=case,
            date_now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )
        return rendered_body


CrmCaseRule()
