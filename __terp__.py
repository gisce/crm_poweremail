{
    "name": "CRM Poweremail",
    "version": "0.1.0",
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
    'update_xml': ['crm_view.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
#    'certificate': 'certificate',
}
