from odoo import models, fields, api
from datetime import timedelta

class BidClosingDaysConfig(models.Model):
    _name = 'bid.closing.days.config'
    _description = 'Bid Closing Days Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Configuration Name',
        default='Bid Closing Days',
        readonly=True
    )

    bid_closing_days = fields.Integer(
        string='Bid Closing Days',
        required=True,
        help="Number of days from bid creation until closing",
        default=30,
        min_value=1
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    @api.constrains('active')
    def _check_single_active_config(self):
        """
        Ensure only one active configuration exists
        """
        for record in self:
            if record.active:
                existing_active = self.search([
                    ('id', '!=', record.id),
                    ('active', '=', True)
                ])
                if existing_active:
                    existing_active.write({'active': False})

    def name_get(self):
        """
        Custom name get to display bid closing days
        """
        result = []
        for record in self:
            name = f"Bid Closing Days: {record.bid_closing_days}"
            result.append((record.id, name))
        return result