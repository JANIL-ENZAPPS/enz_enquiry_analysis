from odoo import api, fields, models


class SalesTargetUser(models.Model):
    _name = 'sales.target.user.enquiry'
    _description = 'Sales Target per User'

    user_id = fields.Many2one('res.users', string="Salesperson", required=True, domain="[('id', 'in', salesperson_ids)]")
    sales_target = fields.Float(string="Sales Target", required=True)
    type = fields.Selection([
        ('month', 'Monthly'),
        ('quarter', 'Quarterly')
    ], string='Period Type', required=True)

    month_period = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month Period')

    quarter = fields.Selection([
        ('q1', 'Q1'),
        ('q2', 'Q2'),
        ('q3', 'Q3'),
        ('q4', 'Q4')
    ], string='Quarter')

    salesperson_ids = fields.Many2many('res.users', compute='_compute_salesperson_ids', store=False, string="Available Salespersons")

    _sql_constraints = [
        ('unique_user_period', 'UNIQUE(user_id, type, month_period, quarter_period)',
         'A sales target for this salesperson and period already exists!')
    ]

    @api.onchange('type')
    def _onchange_type(self):
        """Clear month_period and quarter_period when type changes"""
        self.month_period = False
        self.quarter = False

    @api.onchange('user_id')
    def _compute_salesperson_ids(self):
        for record in self:
            salespersons = self.env['sale.order'].search([]).mapped('user_id')
            record.salesperson_ids = [(6, 0, salespersons.ids)]

    @api.depends('type')
    def _compute_period_readonly(self):
        """Set periods readonly based on type"""
        for record in self:
            record.is_month_readonly = record.type != 'month'
            record.is_quarter_readonly = record.type != 'quarter'

    is_month_readonly = fields.Boolean(compute='_compute_period_readonly')
    is_quarter_readonly = fields.Boolean(compute='_compute_period_readonly')
