# -*- coding: utf-8 -*-
# Delivery time window (merged from delivery_time_custom, same field names so existing
# data is kept when delivery_time_custom is uninstalled after installing this module).
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    from_date = fields.Datetime("From", default=lambda self: fields.Datetime.now() + timedelta(hours=3))
    to_date = fields.Datetime("To", default=lambda self: fields.Datetime.now() + timedelta(hours=3))

    @api.constrains('from_date', 'to_date')
    def _check_dates(self):
        today = fields.Datetime.now()
        for record in self:
            if record.from_date and record.from_date < today:
                record.from_date = today

            if record.to_date and record.to_date < today:
                record.to_date = today

    @api.constrains('from_date', 'to_date')
    def _check_dates_from_to(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_("The 'From' date cannot be greater than the 'To' date."))
