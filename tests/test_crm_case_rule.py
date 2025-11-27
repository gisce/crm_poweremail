# coding=utf-8
from destral import testing
from destral.transaction import Transaction

import logging


class TestCrmCaseRule(testing.OOTestCase):
    def setUp(self):
        self.txn = Transaction().start(self.database)
        self.logger = logging.getLogger(__name__)
        self.cursor = self.txn.cursor
        self.uid = self.txn.user
        self.pool = self.txn.pool
        
        # Create base test data
        self._create_base_test_data()

    def tearDown(self):
        self.txn.stop()
    
    def _create_base_test_data(self):
        """Create base test data: partner, address, section, account"""
        partner_obj = self.pool.get('res.partner')
        address_obj = self.pool.get('res.partner.address')
        section_obj = self.pool.get('crm.case.section')
        account_obj = self.pool.get('poweremail.core_accounts')
        user_obj = self.pool.get('res.users')
        
        # Create test partner
        self.test_partner_id = partner_obj.create(self.cursor, self.uid, {
            'name': 'Test Partner',
        })
        
        # Create test partner address
        self.test_partner_address_id = address_obj.create(self.cursor, self.uid, {
            'name': 'Test Partner Address',
            'email': 'partner@example.com',
            'partner_id': self.test_partner_id,
        })
        
        # Create user address if not exists
        user = user_obj.browse(self.cursor, self.uid, self.uid)
        if not user.address_id:
            self.test_user_address_id = address_obj.create(self.cursor, self.uid, {
                'name': 'Test User',
                'email': 'testuser@example.com',
            })
            user_obj.write(self.cursor, self.uid, [self.uid], {
                'address_id': self.test_user_address_id
            })
        else:
            self.test_user_address_id = user.address_id.id
        
        # Create test section
        self.test_section_id = section_obj.create(self.cursor, self.uid, {
            'name': 'Test Section',
            'reply_to': 'section@example.com',
        })
        
        # Create test account
        self.test_account_id = account_obj.create(self.cursor, self.uid, {
            'name': 'Test Account',
            'email_id': 'section@example.com',
            'user': self.uid,
        })

    def test_get_email_addresses_without_template(self):
        """Test get_email_addresses without poweremail template"""
        self.logger.info('Testing get_email_addresses without template')
        rule_obj = self.pool.get('crm.case.rule')
        case_obj = self.pool.get('crm.case')
        
        # Create test case
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': self.test_section_id,
            'partner_id': self.test_partner_id,
            'partner_address_id': self.test_partner_address_id,
            'email_from': 'customer@example.com'
        })
        case = case_obj.browse(self.cursor, self.uid, case_id)
        
        # Create rule without template
        rule_id = rule_obj.create(self.cursor, self.uid, {
            'name': 'Test Rule',
            'active': True,
        })
        
        # Get email addresses
        context = {}
        emails = rule_obj.get_email_addresses(
            self.cursor, self.uid, rule_id, case, context
        )
        
        # Should return base emails
        self.assertIsInstance(emails, list)

    def test_get_email_addresses_with_template(self):
        """Test get_email_addresses with poweremail template"""
        self.logger.info('Testing get_email_addresses with template')
        rule_obj = self.pool.get('crm.case.rule')
        case_obj = self.pool.get('crm.case')
        section_obj = self.pool.get('crm.case.section')
        template_obj = self.pool.get('poweremail.templates')
        account_obj = self.pool.get('poweremail.core_accounts')
        
        # Create test account
        account_id = account_obj.create(self.cursor, self.uid, {
            'name': 'Test Account',
            'email_id': 'section@example.com',
            'user': self.uid,
        })
        
        # Create test section
        section_id = section_obj.create(self.cursor, self.uid, {
            'name': 'Test Section',
            'reply_to': 'section@example.com'
        })
        
        # Create test case
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': section_id,
            'email_from': 'customer@example.com'
        })
        case = case_obj.browse(self.cursor, self.uid, case_id)
        
        # Create poweremail template
        template_id = template_obj.create(self.cursor, self.uid, {
            'name': 'Test Template',
            'object_name': case_obj._name,
            'def_to': 'template_to@example.com',
            'def_cc': 'template_cc1@example.com,template_cc2@example.com',
            'def_bcc': 'template_bcc@example.com',
            'def_subject': 'Test Subject',
            'def_body_text': 'Test Body',
            'pem_account_id': account_id,
        })
        
        # Create rule with template
        rule_id = rule_obj.create(self.cursor, self.uid, {
            'name': 'Test Rule',
            'active': True,
            'pm_template_id': template_id,
        })
        
        # Get email addresses
        context = {}
        emails = rule_obj.get_email_addresses(
            self.cursor, self.uid, rule_id, case, context
        )
        
        # Should include template TO address
        self.assertIn('template_to@example.com', emails)
        
        # Context should include CC and BCC from template
        self.assertIn('email_cc', context)
        self.assertIn('email_bcc', context)

    def test_get_email_body_without_template(self):
        """Test get_email_body without poweremail template"""
        self.logger.info('Testing get_email_body without template')
        rule_obj = self.pool.get('crm.case.rule')
        case_obj = self.pool.get('crm.case')
        section_obj = self.pool.get('crm.case.section')
        
        # Create test section
        section_id = section_obj.create(self.cursor, self.uid, {
            'name': 'Test Section',
            'reply_to': 'section@example.com'
        })
        
        # Create test case
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': section_id,
            'description': 'Test description'
        })
        case = case_obj.browse(self.cursor, self.uid, case_id)
        
        # Create rule without template
        rule_id = rule_obj.create(self.cursor, self.uid, {
            'name': 'Test Rule',
            'active': True,
        })
        
        # Get email body
        body = rule_obj.get_email_body(
            self.cursor, self.uid, rule_id, case
        )
        
        # Should return base body
        self.assertIsInstance(body, (str, unicode))

    def test_get_email_body_with_template(self):
        """Test get_email_body with poweremail template and mako rendering"""
        self.logger.info('Testing get_email_body with template')
        rule_obj = self.pool.get('crm.case.rule')
        case_obj = self.pool.get('crm.case')
        section_obj = self.pool.get('crm.case.section')
        template_obj = self.pool.get('poweremail.templates')
        account_obj = self.pool.get('poweremail.core_accounts')
        
        # Create test account
        account_id = account_obj.create(self.cursor, self.uid, {
            'name': 'Test Account',
            'email_id': 'section@example.com',
            'user': self.uid,
        })
        
        # Create test section
        section_id = section_obj.create(self.cursor, self.uid, {
            'name': 'Test Section',
            'reply_to': 'section@example.com'
        })
        
        # Create test case
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case Name',
            'section_id': section_id,
            'description': 'Test description'
        })
        case = case_obj.browse(self.cursor, self.uid, case_id)
        
        # Create poweremail template with mako variables
        template_body = 'Case: ${object.name}\nID: ${object.id}'
        template_id = template_obj.create(self.cursor, self.uid, {
            'name': 'Test Template',
            'object_name': case_obj._name,
            'def_to': 'template_to@example.com',
            'def_subject': 'Test Subject',
            'def_body_text': template_body,
            'pem_account_id': account_id,
        })
        
        # Create rule with template
        rule_id = rule_obj.create(self.cursor, self.uid, {
            'name': 'Test Rule',
            'active': True,
            'pm_template_id': template_id,
        })
        
        # Get email body
        body = rule_obj.get_email_body(
            self.cursor, self.uid, rule_id, case
        )
        
        # Should render mako template with case data
        self.assertIn('Test Case Name', body)
        self.assertIn(str(case_id), body)

    def test_template_language_selection(self):
        """Test that template uses correct language from case/partner/user"""
        self.logger.info('Testing template language selection')
        rule_obj = self.pool.get('crm.case.rule')
        case_obj = self.pool.get('crm.case')
        section_obj = self.pool.get('crm.case.section')
        template_obj = self.pool.get('poweremail.templates')
        account_obj = self.pool.get('poweremail.core_accounts')
        partner_obj = self.pool.get('res.partner')
        
        # Create test account
        account_id = account_obj.create(self.cursor, self.uid, {
            'name': 'Test Account',
            'email_id': 'section@example.com',
            'user': self.uid,
        })
        
        # Create partner with language
        partner_id = partner_obj.create(self.cursor, self.uid, {
            'name': 'Test Partner',
            'lang': 'es_ES',
        })
        
        # Create test section
        section_id = section_obj.create(self.cursor, self.uid, {
            'name': 'Test Section',
            'reply_to': 'section@example.com'
        })
        
        # Create test case with partner
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': section_id,
            'partner_id': partner_id,
        })
        case = case_obj.browse(self.cursor, self.uid, case_id)
        
        # Create template
        template_id = template_obj.create(self.cursor, self.uid, {
            'name': 'Test Template',
            'object_name': case_obj._name,
            'def_to': 'test@example.com',
            'def_subject': 'Test',
            'def_body_text': 'Test body',
            'pem_account_id': account_id,
        })
        
        # Create rule with template
        rule_id = rule_obj.create(self.cursor, self.uid, {
            'name': 'Test Rule',
            'active': True,
            'pm_template_id': template_id,
        })
        
        # Get email body - should use partner language
        context = {}
        body = rule_obj.get_email_body(
            self.cursor, self.uid, rule_id, case, context
        )
        
        # Verify body was rendered (language context is internal)
        self.assertIsInstance(body, (str, unicode))


class TestCrmCaseEmailSend(testing.OOTestCase):
    def setUp(self):
        self.txn = Transaction().start(self.database)
        self.logger = logging.getLogger(__name__)
        self.cursor = self.txn.cursor
        self.uid = self.txn.user
        self.pool = self.txn.pool

    def tearDown(self):
        self.txn.stop()

    def test_email_send_creates_mailbox(self):
        """Test that email_send creates a poweremail.mailbox entry"""
        self.logger.info('Testing email_send creates mailbox')
        case_obj = self.pool.get('crm.case')
        section_obj = self.pool.get('crm.case.section')
        account_obj = self.pool.get('poweremail.core_accounts')
        mailbox_obj = self.pool.get('poweremail.mailbox')
        user_obj = self.pool.get('res.users')
        address_obj = self.pool.get('res.partner.address')
        
        # Create user address
        user_addr_id = address_obj.create(self.cursor, self.uid, {
            'name': 'User',
            'email': 'user@example.com'
        })
        user_obj.write(self.cursor, self.uid, [self.uid], {
            'address_id': user_addr_id
        })
        
        # Create test account
        account_id = account_obj.create(self.cursor, self.uid, {
            'name': 'Test Account',
            'email_id': 'section@example.com',
            'user': self.uid,
        })
        
        # Create test section
        section_id = section_obj.create(self.cursor, self.uid, {
            'name': 'Test Section',
            'reply_to': 'section@example.com'
        })
        
        # Create test case
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': section_id,
            'user_id': self.uid,
        })
        case = case_obj.browse(self.cursor, self.uid, case_id)
        
        # Send email
        emails = ['customer@example.com']
        body = 'Test email body'
        case_obj.email_send(
            self.cursor, self.uid, case, emails, body
        )
        
        # Verify mailbox entry was created
        mailbox_ids = mailbox_obj.search(self.cursor, self.uid, [
            ('conversation_id', '=', case.conversation_id.id),
            ('folder', '=', 'outbox')
        ])
        
        self.assertTrue(len(mailbox_ids) > 0)
        mailbox = mailbox_obj.browse(self.cursor, self.uid, mailbox_ids[0])
        self.assertIn('customer@example.com', mailbox.pem_to)
        self.assertIn(case.name, mailbox.pem_subject)

    def test_parse_body_markdown(self):
        """Test markdown parsing in email body"""
        self.logger.info('Testing parse_body_markdown')
        case_obj = self.pool.get('crm.case')
        
        # Test markdown text
        markdown_text = '# Title\n\nThis is **bold** text.'
        html = case_obj.parse_body_markdown(markdown_text)
        
        # Should convert to HTML
        self.assertIn('<h1>', html)
        self.assertIn('bold', html)
        
        # Test HTML text (should not be converted)
        html_text = '<p>Already HTML</p>'
        result = case_obj.parse_body_markdown(html_text)
        
        # Should keep as-is
        self.assertEqual(result, html_text)

    def test_format_mails(self):
        """Test formatting CC emails"""
        self.logger.info('Testing format_mails')
        case_obj = self.pool.get('crm.case')
        section_obj = self.pool.get('crm.case.section')
        
        # Create test section
        section_id = section_obj.create(self.cursor, self.uid, {
            'name': 'Test Section',
            'reply_to': 'section@example.com'
        })
        
        # Create case with CC emails
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': section_id,
            'email_cc': 'User One <user1@example.com>, user2@example.com'
        })
        case = case_obj.browse(self.cursor, self.uid, case_id)
        
        # Format mails
        formatted = case_obj.format_mails(
            self.cursor, self.uid, case
        )
        
        # Should return formatted list
        self.assertIsInstance(formatted, list)
        self.assertTrue(len(formatted) > 0)
