{
    'name': 'Delivery Time',
    'sequence': -999,
    'website': 'https://www.linkedin.com/in/lomixyz/',
    'author': 'Allam Bushra',
    'summary': "Any time after 00:00 means the next day's date.",
    'depends': ['base', 'account', 'qr_code_invoice_app'],
    'data': [
         'views/account_move.xml',
         'views/res_partner.xml',
    ],
    'application': True,
}