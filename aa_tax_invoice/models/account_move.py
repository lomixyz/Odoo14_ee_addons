# -*- coding: utf-8 -*-
import base64
import json
from io import BytesIO

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_repr

try:
    import qrcode
except ImportError:  # pragma: no cover - declared in external_dependencies
    qrcode = None


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Not stored on purpose: only used by the report, so installing the module never has
    # to recompute every invoice line of the database.
    aa_discount_amount = fields.Monetary(string='Discount Amount', compute='_compute_aa_amounts')
    aa_tax_amount = fields.Monetary(string='VAT Amount', compute='_compute_aa_amounts')

    @api.depends('price_unit', 'discount', 'quantity', 'price_subtotal', 'price_total')
    def _compute_aa_amounts(self):
        for line in self:
            line.aa_discount_amount = line.price_unit * line.quantity * (line.discount or 0.0) / 100.0
            line.aa_tax_amount = line.price_total - line.price_subtotal

    def aa_get_vat_rate_label(self):
        """ VAT rate per line as required on the printed invoice, e.g. '15%'. """
        self.ensure_one()
        labels = []
        for tax in self.tax_ids:
            if tax.amount_type in ('percent', 'division'):
                labels.append('{:g}'.format(tax.amount) + '%')
            else:
                labels.append(tax.description or tax.name)
        return ', '.join(labels)


class AccountMove(models.Model):
    _inherit = 'account.move'

    aa_total_discount = fields.Monetary(string='Total Discount', compute='_compute_aa_total_discount')

    @api.depends('invoice_line_ids.price_unit', 'invoice_line_ids.discount', 'invoice_line_ids.quantity')
    def _compute_aa_total_discount(self):
        for move in self:
            move.aa_total_discount = sum(move.invoice_line_ids.mapped('aa_discount_amount'))

    # ------------------------------------------------------------------
    # Invoice type / dates
    # ------------------------------------------------------------------
    def aa_is_simplified(self):
        """ Simplified (B2C) vs standard tax invoice.
        When the ZATCA integration module is installed its invoice type is used, because
        that is the type that gets signed and cleared / reported. Otherwise the customer
        decides: individual -> simplified, company -> standard. """
        self.ensure_one()
        if 'l10n_sa_invoice_type' in self._fields and self.l10n_sa_invoice_type:
            return self.l10n_sa_invoice_type == 'Simplified'
        return not self.partner_id.commercial_partner_id.is_company

    def aa_get_confirmation_datetime(self):
        """ Confirmation date/time of the invoice, from whichever module records it. """
        self.ensure_one()
        for fname in ('sa_confirmation_datetime', 'l10n_sa_confirmation_datetime', 'datetime_invoice'):
            if fname in self._fields and self[fname]:
                return self[fname]
        return False

    def aa_get_supply_date(self):
        self.ensure_one()
        if 'l10n_sa_delivery_date' in self._fields and self.l10n_sa_delivery_date:
            return self.l10n_sa_delivery_date
        return False

    # ------------------------------------------------------------------
    # QR code
    # ------------------------------------------------------------------
    def _aa_zatca_module_installed(self):
        return 'sa_qr_code_str' in self._fields

    def _aa_is_phase2(self):
        """ True when the invoice falls under ZATCA Phase 2 (integration) according to the
        ZATCA integration module settings of the company. """
        self.ensure_one()
        if not self._aa_zatca_module_installed() or not self.is_zatca:
            return False
        phase1_end = self.l10n_sa_phase1_end_date
        if phase1_end:
            ref_date = self.aa_get_confirmation_datetime()
            ref_date = ref_date.date() if ref_date else self.invoice_date
            if ref_date and ref_date <= phase1_end:
                return False
        return True

    def _aa_phase1_qr_str(self):
        """ ZATCA Phase 1 TLV QR: seller name, VAT number, timestamp, total, VAT total. """
        self.ensure_one()

        def tlv(tag, value):
            value = value.encode('UTF-8') if isinstance(value, str) else value
            return tag.to_bytes(1, 'big') + len(value).to_bytes(1, 'big') + value

        confirmation = self.aa_get_confirmation_datetime() or self.create_date
        if not confirmation or not self.company_id.vat:
            return ''
        time_sa = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), confirmation)
        data = (tlv(1, self.company_id.display_name)
                + tlv(2, self.company_id.vat)
                + tlv(3, time_sa.strftime('%Y-%m-%dT%H:%M:%S'))
                + tlv(4, float_repr(abs(self.amount_total), 2))
                + tlv(5, float_repr(abs(self.amount_tax), 2)))
        return base64.b64encode(data).decode()

    def aa_get_qr_info(self):
        """ What the report prints in the QR cell.
        Returns a dict: mode in ('phase2', 'phase1', 'pending', 'draft', 'none'),
        image (data URI or ''), message (str). """
        self.ensure_one()
        info = {'mode': 'none', 'image': '', 'message': ''}
        if self.move_type not in ('out_invoice', 'out_refund'):
            return info
        if self.state != 'posted':
            info.update(mode='draft', message='QR code is generated after the invoice is confirmed')
            return info

        qr_str = ''
        # Posted invoice: a QR is always printed. Phase 2 QR (cleared / signed / signed on
        # print) when it exists; otherwise a QR with the invoice data (tags 1-5).
        qr_str = self._aa_phase2_qr_str() if self._aa_is_phase2() else ''
        if qr_str:
            info['mode'] = 'phase2'
        else:
            qr_str = self._aa_phase1_qr_str()
            info['mode'] = 'phase1' if qr_str else 'none'
            if not qr_str:
                info['message'] = 'QR code not generated: set the company VAT number'
                return info

        info['image'] = self._aa_qr_image(qr_str)
        return info

    @api.model
    def _aa_qr_from_xml(self, b64_xml):
        """ QR embedded in a UBL invoice (AdditionalDocumentReference with ID 'QR'). """
        if not b64_xml:
            return ''
        try:
            root = etree.fromstring(base64.b64decode(b64_xml))
            nodes = root.xpath('//*[local-name()="AdditionalDocumentReference"]'
                               '[*[local-name()="ID"][normalize-space(text())="QR"]]'
                               '//*[local-name()="EmbeddedDocumentBinaryObject"]')
            return (nodes[0].text or '').strip() if nodes else ''
        except Exception:
            return ''

    def _aa_phase2_qr_str(self):
        """ Phase 2 QR (with the cryptographic tags) of a confirmed invoice, best source first:
        - standard: the QR in the cleared XML returned by ZATCA, else the QR of the locally
          signed invoice (before clearance);
        - simplified: the QR in the signed XML that is / will be reported, else the QR
          stored by the ZATCA module.
        l10n_sa_qr_code_str is never used: it can hold the Phase 1 QR of l10n_sa_invoice. """
        self.ensure_one()
        if self.l10n_sa_invoice_type == 'Standard':
            candidates = [self._aa_qr_from_xml(self.zatca_hash_cleared_invoice), self.sa_qr_code_str or '']
            required = {6, 7, 8}
        else:
            candidates = [self._aa_qr_from_xml(self.zatca_invoice), self.sa_qr_code_str or '']
            required = {6, 7, 8, 9}
        for qr in candidates:
            if qr and required <= self._aa_tlv_tags(qr):
                return qr
        return ''

    def _aa_needs_zatca_signature(self):
        self.ensure_one()
        return (self.move_type in ('out_invoice', 'out_refund') and self.state == 'posted'
                and self._aa_is_phase2() and self.zatca_onboarding_status
                and not self.zatca_invoice and not self.zatca_hash_cleared_invoice)

    def _aa_log_sign_error(self, error):
        """ Keep the reason why the Phase 2 QR could not be produced in the chatter
        (once per distinct reason), so it does not have to be printed on the invoice. """
        self.ensure_one()
        body = 'ZATCA Phase 2 QR not generated (invoice could not be signed): %s' % error
        if body not in self.message_ids.mapped('body') and '<p>%s</p>' % body not in self.message_ids.mapped('body'):
            self.message_post(body=body)

    def _aa_ensure_zatca_signed(self):
        """ Sign confirmed Phase 2 invoices that are not signed yet, through the ZATCA
        integration module (create_xml_file: UBL XML + hash + ECDSA signature + QR).
        Nothing is sent to ZATCA. Already signed invoices are never re-signed.
        Returns {move_id: error message} for invoices that could not be signed. """
        errors = {}
        if not self._aa_zatca_module_installed():
            return errors
        for move in self:
            if not move._aa_needs_zatca_signature():
                continue
            try:
                move.create_xml_file()
            except Exception as e:
                self.env.cr.rollback()
                self.env.clear()
                errors[move.id] = getattr(e, 'name', False) or str(e)
                move._aa_log_sign_error(errors[move.id])
        return errors

    @api.model
    def _aa_tlv_tags(self, qr_str):
        """ Set of TLV tag numbers contained in a base64 ZATCA QR string. """
        tags = set()
        try:
            raw = base64.b64decode(qr_str)
            i = 0
            while i + 1 < len(raw):
                tags.add(raw[i])
                i += 2 + raw[i + 1]
        except Exception:
            return set()
        return tags

    @api.model
    def _aa_qr_image(self, value):
        if not value or not qrcode:
            return ''
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
        qr.add_data(value)
        qr.make(fit=True)
        img = qr.make_image()
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return 'data:image/png;base64,%s' % base64.b64encode(buffer.getvalue()).decode()

    def aa_generate_zatca_signed_qr(self):
        """ Action 'Sign for ZATCA (Phase 2 QR)': sign confirmed invoices locally with the
        company CSID through the ZATCA integration module, without sending them. """
        if not self._aa_zatca_module_installed():
            raise UserError(_('The ZATCA Phase 2 integration module (ksa_zatca_integration) is not installed.'))
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund') or move.state != 'posted':
                raise UserError(_('%s: only posted customer invoices and credit notes can be signed.') % move.display_name)
            if not move.is_zatca or not move.zatca_onboarding_status:
                raise UserError(_('%s: ZATCA is not activated or onboarding is not completed for %s.')
                                % (move.display_name, move.company_id.name))
        to_sign = self.filtered(lambda m: m._aa_needs_zatca_signature())
        errors = to_sign._aa_ensure_zatca_signed()
        if errors:
            raise UserError('\n'.join('%s: %s' % (self.browse(mid).display_name, msg) for mid, msg in errors.items()))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('ZATCA'),
                'message': _('%s invoice(s) signed (nothing was sent to ZATCA).') % len(to_sign),
                'sticky': False,
            },
        }

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------
    def aa_get_payment_lines(self):
        self.ensure_one()
        payment = self.invoice_payments_widget
        if not payment or payment == 'false':
            return []
        return json.loads(payment).get('content') or []
