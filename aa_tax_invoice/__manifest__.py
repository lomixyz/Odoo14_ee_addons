# -*- coding: utf-8 -*-
{
    'name': 'Saudi Tax Invoice (ZATCA Phase 2 QR)',
    'version': '14.0.1.5.2',
    'category': 'Accounting/Accounting',
    'summary': 'Bilingual ZATCA tax invoice / simplified tax invoice / credit note report '
               'with the Phase 2 e-invoicing QR code',
    'description': """
Saudi Tax Invoice (ZATCA)
=========================
* Bilingual (Arabic / English) tax invoice report.
* Prints "Tax Invoice" for companies and "Simplified Tax Invoice" for individuals
  (follows the ZATCA invoice type when the ZATCA integration module is installed).
* Credit notes print "Credit Note" / "Simplified Credit Note" with the original
  invoice number, date and the reason for issuance.
* VAT rate per line, line discount and VAT amounts, totals, VAT in SAR for foreign
  currency invoices, payment information.
* Phase 2 QR code for every confirmed invoice, sent to ZATCA or not: invoices that are
  not signed yet are signed locally on print through the ZATCA integration module
  (ksa_zatca_integration) with the company CSID (nothing is sent). Cleared standard
  invoices print the QR of the XML returned by ZATCA; simplified invoices print the QR
  of the signed / reported XML (tags 1-9).
* Delivery time window (From / To) on invoices, printed under the delivery date
  (merged from delivery_time_custom, same fields).
* Every posted invoice always prints a QR code: the Phase 2 QR when it can be produced,
  otherwise a QR with the invoice data (tags 1-5); the reason is logged in the chatter.
    """,
    'author': 'Allam Bushra',
    'website': 'https://www.linkedin.com/in/lomixyz/',
    'license': 'LGPL-3',
    'depends': ['account'],
    'external_dependencies': {'python': ['qrcode']},
    'data': [
        'views/report_assets.xml',
        'report/tax_invoice_report.xml',
        'report/tax_invoice_template.xml',
        'views/zatca_actions.xml',
        'views/delivery_time_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
