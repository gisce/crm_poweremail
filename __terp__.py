{
    "name": "CRM Poweremail",
    "version": "0.2.0",
    "depends": ["base", "crm", "poweremail"],
    "author": "GISCE-TI",
    "category": "CRM",
    "description": """
    This module provide :
        * Integration between CRM and Poweremail
        
    NOTE: Needs poweremail with conversations suport.
          See: https://github.com/openlabs/poweremail/issues/24
    """,
    "init_xml": [],
    'update_xml': ['crm_view.xml', 'crm_data.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
#    'certificate': 'certificate',
}
