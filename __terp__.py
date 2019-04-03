# -*- coding: utf-8 -*-
{
    "name": "CRM Poweremail",
    "description": """
    This module provide :
        * Integration between CRM and Poweremail
        
    NOTE: Needs poweremail with conversations suport.
          See: https://github.com/openlabs/poweremail/issues/24
    """,
    "version": "0.15.3",
    "author": "GISCE-TI",
    "category": "CRM",
    "depends":[
        "base",
        "crm",
        "poweremail",
    ],
    "init_xml": [],
    "demo_xml": [
        "crm_demo.xml",
    ],
    "update_xml":[
        "crm_view.xml",
        "crm_data.xml",
        "res_partner_view.xml",
        "security/ir.model.access.csv",
    ],
    "active": False,
    "installable": True
}
