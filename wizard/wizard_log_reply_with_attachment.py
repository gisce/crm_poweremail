# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from osv import osv, fields
from tools.translate import _


class WizardLogReplyAttachment(osv.osv_memory):
    _name = 'wizard.log.reply.attachment'

    _columns = {
        'case_id': fields.many2one(
            'crm.case', 'CRM case', required=True
        ),
        'file_1': fields.binary('File'),
        'filename_1': fields.char('Filename', size=512),
        'file_2': fields.binary('File'),
        'filename_2': fields.char('Filename', size=512),
        'file_3': fields.binary('File'),
        'filename_3': fields.char('Filename', size=512),
        'file_4': fields.binary('File'),
        'filename_4': fields.char('Filename', size=512),
        'file_5': fields.binary('File'),
        'filename_5': fields.char('Filename', size=512),
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
        conf_obj = self.pool.get('res.config')
        attachment_obj = self.pool.get('ir.attachment')
        wiz = self.browse(cursor, uid, ids[0], context=context)

        ctx = context.copy()
        attachment_ids = []
        total_size = 0
        max_mb_size = float(conf_obj.get(
            cursor, uid, 'crm_poweremail_max_size_mb', 20))
        for x in range(1, 6):
            file_content = getattr(wiz, 'file_{}'.format(x))
            filename = getattr(wiz, 'filename_{}'.format(x))
            if file_content:
                total_size += (len(file_content) * (3.0 / 4.0)) - file_content.count('=', -2)
                attachment_data = {
                    'name': filename,
                    'content': file_content
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
        megas = round(float(total_size)/(1024*1024), 2)
        if megas > max_mb_size:
            raise osv.except_osv(
                _(u"User error"),
                _(
                    u"You are trying to send {}MB. The limit is {}MB"
                ).format(megas, max_mb_size)
            )
        ctx['attachment_ids'] = attachment_ids
        case_obj.case_log_reply(
                cursor, uid, [wiz.case_id.id], context=ctx
        )
        return {}

WizardLogReplyAttachment()
