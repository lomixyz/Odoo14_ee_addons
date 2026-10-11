from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_sequence = fields.Char(string="Invoice Sequence", copy=False, readonly=True, store=True)

    @api.model
    def create(self, vals):
        if vals.get('move_type') == 'out_invoice':
            vals['invoice_sequence'] = self.env['ir.sequence'].next_by_code('account.move.invoice.sequence') or '/'
        return super(AccountMove, self).create(vals)
