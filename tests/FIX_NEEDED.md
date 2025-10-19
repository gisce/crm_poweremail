# Tests - Correccions Necessàries

## Problema
Els tests fallen perquè el mòdul `crm_task` requereix que tots els casos CRM tinguin:
- `partner_id` 
- `partner_address_id`

## Solució Implementada

He afegit un mètode `_create_base_test_data()` al setUp de cada classe de test que crea:

1. **Partner de test** (`self.test_partner_id`)
2. **Adreça del partner** (`self.test_partner_address_id`)
3. **Adreça de l'usuari** (`self.test_user_address_id`) - assignada al usuari actual
4. **Secció CRM** (`self.test_section_id`)
5. **Compte Poweremail** (`self.test_account_id`)

## Fitxers Actualitzats

### ✅ tests/__init__.py - COMPLETAT
- Afegit `_create_base_test_data()` al setUp
- Tots els tests actualitzats per utilitzar `self.test_section_id`, `self.test_partner_id`, etc.

### ✅ tests/test_poweremail_mailbox.py - COMPLETAT  
- Afegit `_create_base_test_data()` al setUp
- Tots els tests amb mocks actualitzats

### ⚠️  tests/test_crm_case_rule.py - PARCIALMENT COMPLETAT
- Afegit `_create_base_test_data()` al setUp de TestCrmCaseRule
- Primer test actualitzat
- **PENDENT**: Actualitzar la resta de tests per utilitzar dades base

## Instruccions per Completar test_crm_case_rule.py

Per cada test que crea un `case_obj.create()`, assegurar que té:

```python
case_id = case_obj.create(self.cursor, self.uid, {
    'name': 'Test Case',
    'section_id': self.test_section_id,           # ← Utilitzar dades base
    'partner_id': self.test_partner_id,            # ← Afegir si no existeix
    'partner_address_id': self.test_partner_address_id,  # ← Afegir si no existeix
    # ... altres camps ...
})
```

I eliminar les creacions redundants de:
- `section_obj.create()` → utilitzar `self.test_section_id`
- `account_obj.create()` → utilitzar `self.test_account_id`

## Tests que Necessiten Actualització

1. `test_get_email_addresses_with_template` - PENDENT
2. `test_get_email_body_without_template` - PENDENT  
3. `test_get_email_body_with_template` - PENDENT
4. `test_template_language_selection` - PENDENT (aquest crea un partner específic amb lang, mantenir-ho)
5. `TestCrmCaseEmailSend.test_email_send_creates_mailbox` - PENDENT
6. `TestCrmCaseEmailSend.test_parse_body_markdown` - OK (no crea casos)
7. `TestCrmCaseEmailSend.test_format_mails` - PENDENT

## Nota Important

El test `test_template_language_selection` crea un partner amb `lang='es_ES'`. Aquest és un cas especial i ha de mantenir la seva pròpia creació de partner, PERÒ el cas ha de tenir també `partner_address_id`:

```python
# Create partner with language
partner_id = partner_obj.create(self.cursor, self.uid, {
    'name': 'Test Partner',
    'lang': 'es_ES',
})

# Create address for this partner
partner_address_id = address_obj.create(self.cursor, self.uid, {
    'name': 'Partner Address',
    'email': 'partner@example.com',
    'partner_id': partner_id,
})

# Create test case with partner
case_id = case_obj.create(self.cursor, self.uid, {
    'name': 'Test Case',
    'section_id': self.test_section_id,
    'partner_id': partner_id,
    'partner_address_id': partner_address_id,  # ← Important!
})
```
