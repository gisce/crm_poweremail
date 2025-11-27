# Test Coverage Summary for crm_poweremail

## Overview
This document provides a summary of the test suite for the crm_poweremail module.

## Test Files

### 1. tests/__init__.py - Main CRM Case Tests

**Class: TestCRMPoweremail**

Tests covering core CRM case functionality with poweremail integration:

- `test_onchange_address_ids()` - Tests the onchange method for CC/BCC address updates
- `test_filter_mails()` - Tests email filtering to remove duplicates and unwanted emails
- `test_add_to_watchers()` - Tests adding addresses to case watchers (CC)
- `test_remove_from_watchers()` - Tests removing addresses from case watchers
- `test_conversation_creation()` - Tests automatic conversation creation with cases
- `test_conversation_name_update()` - Tests conversation name updates when case name changes
- `test_get_cc_emails()` - Tests gathering CC emails from various sources
- `test_get_bcc_emails()` - Tests gathering BCC emails from watchers
- `test_autowatch_adds_current_user()` - Tests that autowatch adds current user to case watchers

### 2. tests/test_poweremail_mailbox.py - Mailbox Integration Tests

**Class: TestPoweremailMailbox**

Tests covering poweremail mailbox and partner address management:

- `test_get_partner_address_from_email_existing()` - Tests retrieving existing partner address from email
- `test_get_partner_address_from_email_new()` - Tests creating new partner address from email
- `test_get_partner_address_from_email_with_domain()` - Tests partner assignment based on email domain
- `test_create_crm_case_from_mail()` - Tests CRM case creation from incoming email
- `test_get_cases_ids_from_references()` - Tests extracting case IDs from email references
- `test_update_case_from_mail()` - Tests updating existing case from incoming email
- `test_mailbox_create_sends_notification()` - **Tests notification sent when receiving email (using mocks)**
- `test_mailbox_create_with_new_conversation()` - Tests new case creation when no conversation exists (using mocks)
- `test_forward_case_response_notification()` - **Tests that watchers receive notification emails (using mocks)**

**Class: TestResPartner**

Tests covering res.partner domain functionality:

- `test_partner_domain_field()` - Tests that partner domain field exists and works
- `test_partner_domain_unique_per_domain()` - Tests multiple partners with different domains

### 3. tests/test_crm_case_rule.py - CRM Rules and Templates Tests

**Class: TestCrmCaseRule**

Tests covering CRM case rules with poweremail templates:

- `test_get_email_addresses_without_template()` - Tests email address gathering without template
- `test_get_email_addresses_with_template()` - Tests email address gathering with template (TO/CC/BCC)
- `test_get_email_body_without_template()` - Tests email body generation without template
- `test_get_email_body_with_template()` - Tests email body generation with Mako template rendering
- `test_template_language_selection()` - Tests correct language selection from partner/user

**Class: TestCrmCaseEmailSend**

Tests covering email sending functionality:

- `test_email_send_creates_mailbox()` - Tests that sending email creates mailbox entry
- `test_parse_body_markdown()` - Tests markdown to HTML conversion in email bodies
- `test_format_mails()` - Tests email address formatting for CC lists

## Key Test Coverage Areas

### 1. Watchers Management
- Adding/removing watchers to CC and BCC
- Synchronizing many2many relations with email string fields
- Filtering duplicate addresses

### 2. Email Processing
- Filtering emails (removing sender, section, duplicates)
- Parsing email addresses with display names
- Creating partner addresses from emails
- Domain-based partner assignment

### 3. Conversation Management
- Automatic conversation creation
- Conversation name synchronization
- Linking emails to conversations
- Case ID extraction from message references

### 4. Template Integration
- Mako template rendering with case data
- Template-based TO/CC/BCC addresses
- Language selection for templates
- Template body rendering

### 5. Email Sending
- Mailbox entry creation
- CC/BCC management
- Signature addition
- Markdown parsing

### 6. Notification System (with Mocks)
- Notification sent when receiving incoming email
- Watchers receive forwarded emails
- New case creation from email without existing conversation
- Mocking email parsing to avoid requiring email system configuration

## Running the Tests

```bash
# Run all tests for the module
destral -m crm_poweremail

# Run specific test file
destral -m crm_poweremail tests/test_poweremail_mailbox.py

# Run specific test class
destral -m crm_poweremail tests/test_poweremail_mailbox.py::TestPoweremailMailbox

# Run specific test method
destral -m crm_poweremail tests/__init__.py::TestCRMPoweremail::test_filter_mails
```

## Test Dependencies

The tests require:
- destral testing framework
- OpenERP/Odoo test database
- poweremail module installed
- crm module installed
- qreu library (for email parsing tests)
- markdown library (for markdown parsing tests)
- mock library (for notification testing without email system configured)

## Notes

- Tests use the destral.testing.OOTestCase framework
- Each test class has setUp/tearDown methods for transaction management
- Tests create test data in the database and clean up in tearDown
- Some tests may skip if optional dependencies (like qreu) are not available
