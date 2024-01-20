# -*- coding: utf-8 -*-
from odoo import api, fields, models

class AccountAccount(models.Model):
    _inherit = 'account.account'

    sh_parent_id = fields.Many2one('account.account', string = "Parent Account",store=True, )

class AccountAccountType(models.Model):
	_inherit = "account.account.type"
	
	type = fields.Selection(selection_add=[('view', 'View')],ondelete={'view': 'cascade'})