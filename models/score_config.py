from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError

class ScoreRangeConfig(models.Model):
    _name = 'enquiry.range.config'
    _description = 'Score Range Configuration'
    _order = 'min_percentage'

    name = fields.Char(string='Range Name', compute='_compute_name', store=True)


    min_percentage = fields.Float(string='Minimum Percentage', required=True)
    max_percentage = fields.Float(string='Maximum Percentage', required=True)
    points = fields.Integer(string='Points', required=True)



    @api.depends( 'min_percentage', 'max_percentage', 'points')
    def _compute_name(self):
        for record in self:
            record.name = f' {record.min_percentage}% - {record.max_percentage}% = {record.points} points'

    @api.constrains('min_percentage', 'max_percentage')
    def _check_percentages(self):
        for record in self:
            if record.min_percentage >= record.max_percentage:
                raise ValidationError('Maximum percentage must be greater than minimum percentage')
            if record.min_percentage < 0 or record.max_percentage > 100:
                raise ValidationError('Percentages must be between 0 and 100')

    _sql_constraints = [
        ('unique_range',
         'unique(min_percentage, max_percentage)',
         'Score range overlapping for this metric type!')
    ]