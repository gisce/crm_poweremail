crm_poweremail
==============

OpenERP CRM Poweremail integration

## Features

- Automatic conversation creation for CRM cases
- Email watchers (CC/BCC) management
- Partner address auto-creation from emails
- Poweremail template integration with CRM rules
- Markdown support in email bodies
- Email filtering and deduplication

## Testing

This module includes comprehensive tests covering:

- CRM case onchange methods for CC/BCC addresses
- Email filtering and deduplication
- Watchers management (add/remove)
- Conversation creation and updates
- Email sending functionality
- Poweremail mailbox integration
- Partner address creation from emails
- CRM case rule template integration
- **Notification system when receiving emails (using mocks)**

To run the tests:

```bash
destral -m crm_poweremail
```

### Testing with Mocks

The notification tests use the `mock` library to simulate email reception and processing without requiring a configured email system. This includes:

- Testing notification emails sent to watchers when a reply is received
- Testing new case creation from incoming emails
- Testing email forwarding to CC/BCC recipients

Test files are located in the `tests/` directory:
- `__init__.py` - Main CRM case tests
- `test_poweremail_mailbox.py` - Mailbox and partner address tests (includes notification mocks)
- `test_crm_case_rule.py` - CRM case rule and template tests