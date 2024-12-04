# -*- coding: utf-8 -*-
{
    'name': "Enquiry Analysis",
    'summary': """
        Display the Status of Enquiry with respect to the User.
        """,
    'description': """
        This module will help to display on current status of the PO,SO,Transfer,Invoice of the enquiry.
    """,
    "author": "Enzapps Private Limited",
    "website": "https://www.enzapps.com",
    'category': 'Extra Tools',
    'version': '16.0.1.2',
    'depends': ['sale','purchase','stock','account','enz_trading_advanced'],
    "images": ['static/description/icon.png'],
    "license": 'OPL-1',
    'data': [
        'security/ir.model.access.csv',
        'views/rank_config.xml',
        'views/score_config.xml',
        'views/bid_close_config.xml',
        'views/achievement.xml',
        'views/sales_target_config.xml',
        'views/views.xml',
        'data/month_data.xml',
    ],
    'installable': True,
    'application': True,
    "price": '100',
    "currency": 'USD',
}