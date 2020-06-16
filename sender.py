# coding=utf-8
from qreu.sendcontext import SMTPSender


class PowerEmailSender(SMTPSender):
    def __init__(self, account):
        super(PowerEmailSender, self).__init__(
            host=account.smtpserver,
            port=account.smtpport,
            user=account.smtpuname,
            passwd=account.smtppass,
            tls=account.smtptls,
            ssl=account.smtpssl
        )
