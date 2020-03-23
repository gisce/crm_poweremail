# -*- encoding: utf-8 -*-

from osv import osv, fields
from tools.translate import _


class WizardLogReplyAttachment(osv.osv_memory):
    _name = 'wizard.log.reply.attachment'

    _columns = {
        'case_id': fields.many2one(
            'crm.case', 'CRM case', required=True
        ),
        'file': fields.binary('File'),
        'filename': fields.char('Filename', size=512),
        'add_attachment': fields.boolean('Send with attachment?'),
        'info': fields.text('Info')
    }

    _defaults = {
        'case_id': lambda *a: a[3].get('active_id', False),
        'info': lambda *a: _('Select a file to send as an attachment')
    }

    def log_reply(self, cursor, uid, ids, context=None):
        if context is None:
            context = {}
        case_obj = self.pool.get('crm.case')
        attachment_obj = self.pool.get('ir.attachment')
        wiz = self.browse(cursor, uid, ids[0], context=context)

        ctx = context.copy()
        attachment_ids = []
        if wiz.file:
            attachment_data = {
                'name': wiz.filename,
                'content': wiz.file
            }
            att_id = attachment_obj.create(cursor, uid, {
                'description': _(
                    "From CRM case [{}] {}"
                ).format(wiz.case_id.id, wiz.case_id.name),
                'datas_fname': attachment_data['name'],
                'name': attachment_data['name'],
                'datas': attachment_data['content'],
                'res_model': 'crm.case',
                'res_id': wiz.case_id.id
            })
            attachment_ids.append(att_id)
        ctx['attachment_ids'] = attachment_ids
        case_obj.case_log_reply(
                cursor, uid, [wiz.case_id.id], context=ctx
        )
        return {}

WizardLogReplyAttachment()
