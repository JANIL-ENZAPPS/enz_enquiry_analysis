from odoo import models, fields, api
from datetime import datetime, timedelta


class SalesBadgeAssignmentConfig(models.Model):
    _name = 'enquiry.badge.assignment.config'
    _description = 'Badge Assignment Configuration'
    _rec_name = 'badge'

    min_score = fields.Integer(string='Minimum Score', required=True)
    max_score = fields.Integer(string='Maximum Score', required=True)
    badge = fields.Selection([
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('bronze', 'Bronze'),
        ('none', 'No Badge')
    ], string='Badge', required=True, default='none')