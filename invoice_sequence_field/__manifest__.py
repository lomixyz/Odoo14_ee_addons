{
    'name': 'Invoice Sequence Reference',
    'version': '14.0.1.0.0',
    'summary': 'Adds a sequenced field to invoices',
    'category': 'Accounting',
    'author': 'Allam Bushra',
    'depends': ['base', 'account'],
    'data': [
        'data/sequence_data.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': True,
}
