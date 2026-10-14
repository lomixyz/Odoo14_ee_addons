# -*- coding: utf-8 -*-
from odoo import models

AA_REPORT = 'aa_tax_invoice.report_tax_invoice'


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_html(self, docids, data=None):
        """ Before rendering the ZATCA tax invoice, sign the confirmed Phase 2 invoices
        that are not signed yet, so their Phase 2 QR code can be printed even when the
        invoice has not been sent to ZATCA. Signing errors are shown in the QR cell. """
        if self.report_name == AA_REPORT and docids:
            errors = self.env['account.move'].browse(docids)._aa_ensure_zatca_signed()
            if errors:
                self = self.with_context(aa_zatca_sign_errors=errors)
        return super(IrActionsReport, self)._render_qweb_html(docids, data=data)
