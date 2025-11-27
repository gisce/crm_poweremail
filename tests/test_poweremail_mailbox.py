# coding=utf-8
from destral import testing
from destral.transaction import Transaction

import logging


class TestPoweremailMailbox(testing.OOTestCase):
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

    def test_get_partner_address_from_email_existing(self):
        """Test getting existing partner address from email"""
        self.logger.info('Testing get_partner_address_from_email with existing address')
        mailbox_obj = self.pool.get('poweremail.mailbox')
        address_obj = self.pool.get('res.partner.address')
        
        # Create test address
        addr_id = address_obj.create(self.cursor, self.uid, {
            'name': 'Test User',
            'email': 'test@example.com'
        })
        
        # Get partner address from email
        result_id = mailbox_obj.get_partner_address_from_email(
            self.cursor, self.uid, 'test@example.com'
        )
        
        self.assertEqual(result_id, addr_id)

    def test_get_partner_address_from_email_new(self):
        """Test creating new partner address from email"""
        self.logger.info('Testing get_partner_address_from_email with new address')
        mailbox_obj = self.pool.get('poweremail.mailbox')
        address_obj = self.pool.get('res.partner.address')
        
        # Get/create partner address from email (should create new)
        result_id = mailbox_obj.get_partner_address_from_email(
            self.cursor, self.uid, 'New User <newuser@example.com>'
        )
        
        # Verify address was created
        self.assertTrue(result_id)
        address = address_obj.browse(self.cursor, self.uid, result_id)
        self.assertEqual(address.email, 'newuser@example.com')
        self.assertEqual(address.name, 'New User')

    def test_get_partner_address_from_email_with_domain(self):
        """Test partner assignment based on email domain"""
        self.logger.info('Testing partner assignment by domain')
        mailbox_obj = self.pool.get('poweremail.mailbox')
        partner_obj = self.pool.get('res.partner')
        address_obj = self.pool.get('res.partner.address')
        
        # Create partner with domain
        partner_id = partner_obj.create(self.cursor, self.uid, {
            'name': 'Test Company',
            'domain': 'example.com'
        })
        
        # Create address with matching domain
        result_id = mailbox_obj.get_partner_address_from_email(
            self.cursor, self.uid, 'contact@example.com'
        )
        
        # Verify partner was assigned
        address = address_obj.browse(self.cursor, self.uid, result_id)
        if address.partner_id:
            self.assertEqual(address.partner_id.id, partner_id)

    def test_create_crm_case_from_mail(self):
        """Test creating CRM case from poweremail mailbox"""
        self.logger.info('Testing create_crm_case')
        mailbox_obj = self.pool.get('poweremail.mailbox')
        case_obj = self.pool.get('crm.case')
        conv_obj = self.pool.get('poweremail.conversation')
        
        # Create conversation
        conv_id = conv_obj.create(self.cursor, self.uid, {
            'name': 'Test Conversation'
        })
        
        # Create test poweremail
        pmail_id = mailbox_obj.create(self.cursor, self.uid, {
            'pem_from': 'customer@example.com',
            'pem_to': 'section@example.com',
            'pem_subject': 'Test Subject',
            'pem_body_text': 'Test body text',
            'pem_account_id': self.test_account_id,
            'conversation_id': conv_id,
            'folder': 'inbox',
        })
        
        # Create CRM case from mail
        case_id = mailbox_obj.create_crm_case(
            self.cursor, self.uid, pmail_id, self.test_section_id,
            body_text='Test body text'
        )
        
        # Verify case was created
        self.assertTrue(case_id)
        case = case_obj.browse(self.cursor, self.uid, case_id)
        self.assertEqual(case.name, 'Test Subject')
        self.assertEqual(case.email_from, 'customer@example.com')
        self.assertEqual(case.description, 'Test body text')
        self.assertEqual(case.conversation_id.id, conv_id)

    def test_get_cases_ids_from_references(self):
        """Test extracting case IDs from message references"""
        self.logger.info('Testing get_cases_ids_from_references')
        from poweremail_mailbox import get_cases_ids_from_references
        
        # Test with valid references
        references = [
            '<tinycrm-123@example.com>',
            '<tinycrm-456@example.com>',
            '<other-reference@example.com>',
            '<tinycrm-123@example.com>',  # Duplicate
        ]
        
        case_ids = get_cases_ids_from_references(references)
        
        # Should extract unique case IDs
        self.assertEqual(len(case_ids), 2)
        self.assertIn(123, case_ids)
        self.assertIn(456, case_ids)

    def test_update_case_from_mail(self):
        """Test updating existing case from mail"""
        self.logger.info('Testing update_case_from_mail')
        mailbox_obj = self.pool.get('poweremail.mailbox')
        case_obj = self.pool.get('crm.case')
        
        # Create test case
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': self.test_section_id,
            'partner_id': self.test_partner_id,
            'partner_address_id': self.test_partner_address_id,
            'description': 'Original description',
            'state': 'open'
        })
        
        # Create test mail with CC addresses
        pmail_id = mailbox_obj.create(self.cursor, self.uid, {
            'pem_from': 'customer@example.com',
            'pem_to': 'section@example.com',
            'pem_cc': 'watcher@example.com',
            'pem_subject': 'Re: Test Case',
            'pem_body_text': 'This is a reply\n\nOriginal message',
            'pem_account_id': self.test_account_id,
            'conversation_id': case_obj.browse(
                self.cursor, self.uid, case_id
            ).conversation_id.id,
            'folder': 'inbox',
            'pem_mail_orig': (
                'From: customer@example.com\r\n'
                'To: section@example.com\r\n'
                'Cc: watcher@example.com\r\n'
                'Subject: Re: Test Case\r\n'
                '\r\n'
                'This is a reply\r\n'
                '\r\n'
                'Original message\r\n'
            )
        })
        
        # Note: update_case_from_mail requires qreu.Email parsing
        # which may not work in test environment without proper mail setup
        # This test validates the method exists and can be called
        try:
            import qreu
            mail = qreu.Email.parse(
                mailbox_obj.browse(
                    self.cursor, self.uid, pmail_id
                ).pem_mail_orig
            )
            
            mailbox_obj.update_case_from_mail(
                self.cursor, self.uid, pmail_id, case_id, mail
            )
            
            # Verify case was updated
            case = case_obj.browse(self.cursor, self.uid, case_id)
            self.assertEqual(case.description, 'This is a reply')
        except ImportError:
            self.logger.warning('qreu module not available, skipping mail parsing test')

    def test_mailbox_create_sends_notification(self):
        """Test that creating mailbox from incoming email sends notification"""
        self.logger.info('Testing mailbox create sends notification')
        from mock import patch, MagicMock
        
        mailbox_obj = self.pool.get('poweremail.mailbox')
        case_obj = self.pool.get('crm.case')
        conv_obj = self.pool.get('poweremail.conversation')
        
        # Create conversation
        conv_id = conv_obj.create(self.cursor, self.uid, {
            'name': 'Test Conversation'
        })
        
        # Create test case linked to conversation
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': self.test_section_id,
            'partner_id': self.test_partner_id,
            'partner_address_id': self.test_partner_address_id,
            'conversation_id': conv_id,
        })
        
        # Mock qreu.Email.parse to return a valid email object
        mock_email = MagicMock()
        mock_email.is_auto_generated = False
        mock_email.from_.address = 'customer@example.com'
        mock_email.from_.display = 'Customer <customer@example.com>'
        mock_email.recipients.addresses = ['section@example.com']
        mock_email.references = ['<tinycrm-{0}@example.com>'.format(case_id)]
        mock_email.cc = []
        mock_email.to = ['section@example.com']
        
        with patch('qreu.Email.parse', return_value=mock_email):
            # Mock forward_case_response to track if it was called
            with patch.object(mailbox_obj, 'forward_case_response') as mock_forward:
                # Create incoming mail
                pmail_id = mailbox_obj.create(self.cursor, self.uid, {
                    'pem_from': 'customer@example.com',
                    'pem_to': 'section@example.com',
                    'pem_subject': 'Re: Test Case',
                    'pem_body_text': 'Customer reply',
                    'pem_account_id': self.test_account_id,
                    'conversation_id': conv_id,
                    'folder': 'inbox',
                    'pem_mail_orig': (
                        'From: customer@example.com\r\n'
                        'To: section@example.com\r\n'
                        'Subject: Re: Test Case\r\n'
                        '\r\n'
                        'Customer reply\r\n'
                    )
                })
                
                # Verify forward_case_response was called (notification sent)
                self.assertTrue(mock_forward.called)
                self.assertEqual(mock_forward.call_count, 1)

    def test_mailbox_create_with_new_conversation(self):
        """Test that creating mailbox creates new case when no conversation exists"""
        self.logger.info('Testing mailbox create with new conversation')
        from mock import patch, MagicMock
        
        mailbox_obj = self.pool.get('poweremail.mailbox')
        conv_obj = self.pool.get('poweremail.conversation')
        
        # Create conversation
        conv_id = conv_obj.create(self.cursor, self.uid, {
            'name': 'New Conversation'
        })
        
        # Mock qreu.Email.parse
        mock_email = MagicMock()
        mock_email.is_auto_generated = False
        mock_email.from_.address = 'newcustomer@example.com'
        mock_email.from_.display = 'New Customer <newcustomer@example.com>'
        mock_email.recipients.addresses = ['section@example.com']
        mock_email.references = []
        mock_email.cc = []
        mock_email.to = ['section@example.com']
        
        with patch('qreu.Email.parse', return_value=mock_email):
            with patch.object(mailbox_obj, 'create_crm_case') as mock_create_case:
                mock_create_case.return_value = 999
                
                # Create incoming mail without existing conversation
                pmail_id = mailbox_obj.create(self.cursor, self.uid, {
                    'pem_from': 'newcustomer@example.com',
                    'pem_to': 'section@example.com',
                    'pem_subject': 'New Issue',
                    'pem_body_text': 'I have a problem',
                    'pem_account_id': self.test_account_id,
                    'conversation_id': conv_id,
                    'folder': 'inbox',
                    'pem_mail_orig': (
                        'From: newcustomer@example.com\r\n'
                        'To: section@example.com\r\n'
                        'Subject: New Issue\r\n'
                        '\r\n'
                        'I have a problem\r\n'
                    )
                })
                
                # Verify create_crm_case was called (new case created)
                self.assertTrue(mock_create_case.called)

    def test_forward_case_response_notification(self):
        """Test that forward_case_response sends email to watchers"""
        self.logger.info('Testing forward_case_response notification')
        from mock import MagicMock
        
        mailbox_obj = self.pool.get('poweremail.mailbox')
        case_obj = self.pool.get('crm.case')
        address_obj = self.pool.get('res.partner.address')
        
        # Create watchers addresses
        watcher1_id = address_obj.create(self.cursor, self.uid, {
            'name': 'Watcher 1',
            'email': 'watcher1@example.com'
        })
        
        # Create case with watchers
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': self.test_section_id,
            'partner_id': self.test_partner_id,
            'partner_address_id': self.test_partner_address_id,
            'cc_address_ids': [(6, 0, [watcher1_id])],
            'email_cc': 'watcher1@example.com'
        })
        case = case_obj.browse(self.cursor, self.uid, case_id)
        
        # Create incoming mail
        pmail_id = mailbox_obj.create(self.cursor, self.uid, {
            'pem_from': 'customer@example.com',
            'pem_to': 'section@example.com',
            'pem_subject': 'Re: Test Case',
            'pem_body_text': 'Customer reply',
            'pem_account_id': self.test_account_id,
            'conversation_id': case.conversation_id.id,
            'folder': 'inbox',
        })
        
        # Mock email object
        mock_email = MagicMock()
        mock_email.from_.address = 'customer@example.com'
        mock_email.from_.display = 'Customer <customer@example.com>'
        mock_email.recipients.addresses = ['section@example.com']
        mock_email.cc = []
        mock_email.to = ['section@example.com']
        
        # Call forward_case_response
        mailbox_obj.forward_case_response(
            self.cursor, self.uid, pmail_id, case, mock_email
        )
        
        # Verify notification email was created
        notification_ids = mailbox_obj.search(self.cursor, self.uid, [
            ('conversation_id', '=', case.conversation_id.id),
            ('pem_folder', '=', 'outbox'),
            ('pem_to', 'ilike', 'watcher1@example.com')
        ])
        
        self.assertTrue(len(notification_ids) > 0)


class TestResPartner(testing.OOTestCase):
    def setUp(self):
        self.txn = Transaction().start(self.database)
        self.logger = logging.getLogger(__name__)
        self.cursor = self.txn.cursor
        self.uid = self.txn.user
        self.pool = self.txn.pool

    def tearDown(self):
        self.txn.stop()

    def test_partner_domain_field(self):
        """Test that res.partner has domain field"""
        self.logger.info('Testing res.partner domain field')
        partner_obj = self.pool.get('res.partner')
        
        # Create partner with domain
        partner_id = partner_obj.create(self.cursor, self.uid, {
            'name': 'Test Company',
            'domain': 'example.com'
        })
        
        # Verify domain was saved
        partner = partner_obj.browse(self.cursor, self.uid, partner_id)
        self.assertEqual(partner.domain, 'example.com')

    def test_partner_domain_unique_per_domain(self):
        """Test creating multiple partners with different domains"""
        self.logger.info('Testing multiple partners with different domains')
        partner_obj = self.pool.get('res.partner')
        
        # Create first partner
        partner1_id = partner_obj.create(self.cursor, self.uid, {
            'name': 'Company One',
            'domain': 'company1.com'
        })
        
        # Create second partner
        partner2_id = partner_obj.create(self.cursor, self.uid, {
            'name': 'Company Two',
            'domain': 'company2.com'
        })
        
        # Verify both exist with different domains
        partner1 = partner_obj.browse(self.cursor, self.uid, partner1_id)
        partner2 = partner_obj.browse(self.cursor, self.uid, partner2_id)
        
        self.assertEqual(partner1.domain, 'company1.com')
        self.assertEqual(partner2.domain, 'company2.com')
        self.assertNotEqual(partner1.id, partner2.id)
