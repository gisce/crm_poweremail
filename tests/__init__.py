# coding=utf-8
from destral import testing
from destral.transaction import Transaction

import logging


class TestCRMPoweremail(testing.OOTestCase):
    def setUp(self):
        self.txn = Transaction().start(self.database)
        self.logger = logging.getLogger(__name__)
        self.cursor = self.txn.cursor
        self.uid = self.txn.user
        self.pool = self.txn.pool
        
        # Create base test data needed for crm_task compatibility
        self._create_base_test_data()

    def tearDown(self):
        self.txn.stop()
    
    def _create_base_test_data(self):
        """Create base test data: partner, address, user address, section"""
        partner_obj = self.pool.get('res.partner')
        address_obj = self.pool.get('res.partner.address')
        user_obj = self.pool.get('res.users')
        section_obj = self.pool.get('crm.case.section')
        
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

    def _check_onchange(self, emails, case_id, mail_type):
        case_obj = self.pool.get('crm.case')
        case = case_obj.browse(self.cursor, self.uid, case_id)
        case_mails = ''
        if mail_type == 'cc':
            case_mails = case.email_cc
        elif mail_type == 'bcc':
            case_mails = case.email_bcc
        self.assertEqual(case_mails, emails,
                         msg='Case emails:\n'
                             '{}\n'
                             '\tDo not match with expected\n'
                             '{}'.format(case_mails, emails))
        appended_string = (
            u'testing@example.com, {}'.format(emails)
        )
        not_appended_string = emails
        changed_addresses = case._onchange_address_ids(mail_type, [[1, 1, [1]]])
        self.assertEqual(
            changed_addresses['value']['email_{}'.format(mail_type)],
            appended_string,
            msg='Appended string:\n'
                '{}\n'
                '\tDoes not match with the new addresses:\n'
                '{}'.format(
                changed_addresses['value']['email_{}'.format(mail_type)],
                appended_string
            )
        )
        vals = {
            'email_{}'.format(mail_type): appended_string,
            '{}_address_ids'.format(mail_type): [[6, 0, [1]]]
        }
        case.write(vals)
        case = case_obj.browse(self.cursor, self.uid, case_id)
        changed_addresses = case._onchange_address_ids(mail_type, [[1, 1, []]])
        self.assertEqual(
            changed_addresses['value']['email_{}'.format(mail_type)],
            not_appended_string,
            msg='Removing address string:\n'
                '{}\n'
                '\tDoes not match with the new addresses:\n'
                '{}'.format(
                case._onchange_address_ids(mail_type, [[1, 1, []]]),
                not_appended_string
            )
        )

    def test_onchange_address_ids(self):
        # def _onchange_address_ids(
        # cursor, uid, ids,addr_type=False, addr_ids=False,context=None
        imod_obj = self.pool.get('ir.model.data')
        address_obj = self.pool.get('res.partner.address')
        address_obj.write(
            self.cursor, self.uid, 1, {'email': 'testing@example.com'})
        case_id = imod_obj.get_object_reference(
            self.cursor, self.uid, 'crm', 'crmpoweremail_case01')[1]
        orig_mails_cc = 'test2@mail.com, me@example.com'
        orig_mails_bcc = 'test@mail.com, test@example.com'
        self.logger.info('Testing onchange for CC')
        self._check_onchange(emails=orig_mails_cc,
                             case_id=case_id,
                             mail_type='cc')
        self.logger.info('Testing onchange for BCC')
        self._check_onchange(emails=orig_mails_bcc,
                             case_id=case_id,
                             mail_type='bcc')

    def test_filter_mails(self):
        """Test filter_mails method removes duplicates and unwanted emails"""
        self.logger.info('Testing filter_mails')
        case_obj = self.pool.get('crm.case')
        
        # Create a test case with base data
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': self.test_section_id,
            'partner_id': self.test_partner_id,
            'partner_address_id': self.test_partner_address_id,
            'email_from': 'from@example.com'
        })
        case = case_obj.browse(self.cursor, self.uid, case_id)
        
        # Test emails with duplicates and emails to filter
        emails = [
            'user1@example.com',
            'from@example.com',  # Should be filtered (email_from)
            'user1@example.com',  # Duplicate
            'section@example.com',  # Should be filtered (section reply_to)
            'user2@example.com',
            '',  # Empty email
        ]
        
        filtered = case_obj.filter_mails(
            emails, 'from@example.com', case, []
        )
        
        # Should only have user1 and user2
        self.assertEqual(len(filtered), 2)
        self.assertIn('user1@example.com', filtered)
        self.assertIn('user2@example.com', filtered)
        self.assertNotIn('from@example.com', filtered)
        self.assertNotIn('section@example.com', filtered)

    def test_add_to_watchers(self):
        """Test adding addresses to watchers (CC)"""
        self.logger.info('Testing add_to_watchers')
        case_obj = self.pool.get('crm.case')
        address_obj = self.pool.get('res.partner.address')
        
        # Create test addresses
        addr1_id = address_obj.create(self.cursor, self.uid, {
            'name': 'User 1',
            'email': 'user1@example.com'
        })
        addr2_id = address_obj.create(self.cursor, self.uid, {
            'name': 'User 2',
            'email': 'user2@example.com'
        })
        
        # Create test case
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': self.test_section_id,
            'partner_id': self.test_partner_id,
            'partner_address_id': self.test_partner_address_id,
        })
        
        # Add addresses to watchers
        case_obj.add_to_watchers(
            self.cursor, self.uid, case_id, [addr1_id, addr2_id], bcc=False
        )
        
        # Verify addresses were added
        case = case_obj.browse(self.cursor, self.uid, case_id)
        cc_addr_ids = [addr.id for addr in case.cc_address_ids]
        self.assertIn(addr1_id, cc_addr_ids)
        self.assertIn(addr2_id, cc_addr_ids)

    def test_remove_from_watchers(self):
        """Test removing addresses from watchers"""
        self.logger.info('Testing remove_from_watchers')
        case_obj = self.pool.get('crm.case')
        address_obj = self.pool.get('res.partner.address')
        
        # Create test addresses
        addr1_id = address_obj.create(self.cursor, self.uid, {
            'name': 'User 1',
            'email': 'user1@example.com'
        })
        addr2_id = address_obj.create(self.cursor, self.uid, {
            'name': 'User 2',
            'email': 'user2@example.com'
        })
        
        # Create test case with watchers
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': self.test_section_id,
            'partner_id': self.test_partner_id,
            'partner_address_id': self.test_partner_address_id,
            'cc_address_ids': [(6, 0, [addr1_id, addr2_id])]
        })
        
        # Remove one address
        case_obj.remove_from_watchers(
            self.cursor, self.uid, case_id, [addr1_id], bcc=False
        )
        
        # Verify address was removed
        case = case_obj.browse(self.cursor, self.uid, case_id)
        cc_addr_ids = [addr.id for addr in case.cc_address_ids]
        self.assertNotIn(addr1_id, cc_addr_ids)
        self.assertIn(addr2_id, cc_addr_ids)

    def test_conversation_creation(self):
        """Test that conversation is created automatically with case"""
        self.logger.info('Testing conversation creation')
        case_obj = self.pool.get('crm.case')
        
        # Create case without conversation
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': self.test_section_id,
            'partner_id': self.test_partner_id,
            'partner_address_id': self.test_partner_address_id,
        })
        
        # Verify conversation was created
        case = case_obj.browse(self.cursor, self.uid, case_id)
        self.assertTrue(case.conversation_id)
        self.assertIn('[%s]' % case_id, case.conversation_id.name)
        self.assertIn('Test Case', case.conversation_id.name)

    def test_conversation_name_update(self):
        """Test that conversation name updates when case name changes"""
        self.logger.info('Testing conversation name update')
        case_obj = self.pool.get('crm.case')
        
        # Create case
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Original Name',
            'section_id': self.test_section_id,
            'partner_id': self.test_partner_id,
            'partner_address_id': self.test_partner_address_id,
        })
        
        # Update case name
        case_obj.write(self.cursor, self.uid, [case_id], {
            'name': 'Updated Name'
        })
        
        # Verify conversation name was updated
        case = case_obj.browse(self.cursor, self.uid, case_id)
        self.assertIn('[%s]' % case_id, case.conversation_id.name)
        self.assertIn('Updated Name', case.conversation_id.name)

    def test_get_cc_emails(self):
        """Test get_cc_emails includes case responsible and partner emails"""
        self.logger.info('Testing get_cc_emails')
        case_obj = self.pool.get('crm.case')
        user_obj = self.pool.get('res.users')
        
        # Get current user email
        user = user_obj.browse(self.cursor, self.uid, self.uid)
        user_email = user.address_id.email if user.address_id else None
        
        # Create case
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': self.test_section_id,
            'partner_id': self.test_partner_id,
            'partner_address_id': self.test_partner_address_id,
            'user_id': self.uid,
            'email_from': 'partner@example.com',
            'email_cc': 'watcher@example.com'
        })
        
        # Get CC emails
        cc_emails = case_obj.get_cc_emails(
            self.cursor, self.uid, case_id, context={}
        )
        
        # Verify emails are included
        self.assertIn('partner@example.com', cc_emails)
        if user_email:
            self.assertIn(user_email, cc_emails)
        self.assertIn('watcher@example.com', cc_emails)

    def test_get_bcc_emails(self):
        """Test get_bcc_emails includes watchers BCC"""
        self.logger.info('Testing get_bcc_emails')
        case_obj = self.pool.get('crm.case')
        
        # Create case with BCC watchers
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': self.test_section_id,
            'partner_id': self.test_partner_id,
            'partner_address_id': self.test_partner_address_id,
            'email_bcc': 'secret1@example.com, secret2@example.com'
        })
        
        # Get BCC emails
        bcc_emails = case_obj.get_bcc_emails(
            self.cursor, self.uid, case_id, context={}
        )
        
        # Verify BCC emails are included
        self.assertIn('secret1@example.com', bcc_emails)
        self.assertIn('secret2@example.com', bcc_emails)

    def test_autowatch_adds_current_user(self):
        """Test autowatch adds current user to watchers"""
        self.logger.info('Testing autowatch')
        case_obj = self.pool.get('crm.case')
        
        # Create case
        case_id = case_obj.create(self.cursor, self.uid, {
            'name': 'Test Case',
            'section_id': self.test_section_id,
            'partner_id': self.test_partner_id,
            'partner_address_id': self.test_partner_address_id,
        })
        
        # Call autowatch
        case_obj.autowatch(self.cursor, self.uid, [case_id])
        
        # Verify current user address was added to watchers
        case = case_obj.browse(self.cursor, self.uid, case_id)
        cc_addr_ids = [addr.id for addr in case.cc_address_ids]
        self.assertIn(self.test_user_address_id, cc_addr_ids)
