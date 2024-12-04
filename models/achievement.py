from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.exceptions import UserError,ValidationError

class PerformanceMonth(models.Model):
    _name = 'user.performance.month'
    _description = 'Performance Month'

    name = fields.Char(string='Month', required=True)

class UserEnquiryPerformance(models.Model):
    _name = 'user.performance'
    _description = 'User Performance Records'

    user_id = fields.Many2one('res.users', string='Users')
    month_ids = fields.Many2many('user.performance.month', string='Months', required=True)
    achievement_level = fields.Selection([
        ('superb', 'Superb Performer'),
        ('best', 'Best Performer'),
        ('good', 'Good Performer')
    ], string='Achievement Level', required=True)
    year = fields.Char(string='Year', default=lambda self: fields.Date.today().year)

    @api.constrains('user_id', 'year', 'month_ids', 'achievement_level')
    def _check_unique_achievement_level(self):
        for record in self:
            # Search for existing records with overlapping months and achievement level
            overlapping_records = self.search([
                ('id', '!=', record.id),
                ('year', '=', record.year),
                ('achievement_level', '=', record.achievement_level),
                ('month_ids', '=', record.month_ids.ids)
            ])

            if overlapping_records:
                # If found, remove the previous record's performance
                overlapping_records.unlink()



class UserPerformanceWizard(models.TransientModel):
    _name = 'user.performance.wizard'
    _description = 'Performance Rating Wizard'

    user_id = fields.Many2one('res.users', string='User', readonly=True)
    name = fields.Char(string='Name', readonly=True)
    month_ids = fields.Many2many('user.performance.month', string='Months', required=True)
    achievement_level = fields.Selection([
        ('superb', 'Superb Performer'),
        ('best', 'Best Performer'),
        ('good', 'Good Performer')
    ], string='Achievement Level', required=True)
    active_id = fields.Integer(string='Active id')
    has_achievement = fields.Boolean(string="Has Achievement")
    old_achievement_level = fields.Selection([
        ('superb', 'Superb Performer'),
        ('best', 'Best Performer'),
        ('good', 'Good Performer')
    ], string='Previous Achievement Level')
    @api.model
    def default_get(self, fields):
        res = super(UserPerformanceWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        res['active_id'] = self.env.context.get('active_id')
        print("active id",active_id,res['active_id'])
        if active_id:
            record = self.env['enquiry.performance.analysis'].browse(active_id)

            if record.user_id:
                res['user_id'] = record.user_id.id
                res['name'] = record.user_id.name
            if record.has_achievement:
                res['has_achievement'] = record.has_achievement
            if record.has_achievement:
                res['old_achievement_level'] = record.achievement_level
            # Automatically calculate months based on date_from and date_to
            date_from = record.date_from
            date_to = record.date_to
            month_ids = []
            if date_from and date_to:
                print("date",date_from,date_to)
                # Generate all months between date_from and date_to
                current_date = date_from
                while current_date <= date_to:
                    month_name = current_date.strftime('%B %Y')
                    print("month",month_name)
                    # Search or create the month record
                    month_record = self.env['user.performance.month'].search([('name', '=', month_name)], limit=1)
                    if not month_record:
                        month_record = self.env['user.performance.month'].create({'name': month_name})
                    month_ids.append(month_record.id)
                    # Move to the next month
                    current_date += relativedelta(months=1)
            res['month_ids'] = [(6, 0, month_ids)]  # [(6, 0, ids)] format to set Many2many field
        return res


    def action_submit(self):
        self.ensure_one()
        record = self.env['enquiry.performance.analysis'].browse(self.active_id)
        vals = {
            'month_ids': [(6, 0, self.month_ids.ids)],
            'achievement_level': self.achievement_level,
            'year':record.date_from.year,
        }
        if self.user_id:
            vals['user_id'] = self.user_id.id
            self.env['user.performance'].create(vals)
            self.env['user.performance.record.line'].create({

                'wizard_id': record.id,
                'name': self.user_id.name,
                'month_ids': [(6, 0, self.month_ids.ids)],
                'year': record.date_from.year,
                'achievement_level': self.achievement_level,
            })


        datas = self.env['enquiry.performance.analysis'].search([])
        print("datas", datas)
        for data in datas:
            data.compute_performance_records()
            data._compute_achievement_level()
            data._compute_has_achievement()
        return {'type': 'ir.actions.act_window_close'}

    def action_reassign(self):
        self.ensure_one()
        record = self.env['enquiry.performance.analysis'].browse(self.active_id)

        # Prepare search domain based on employee or salesperson
        if self.user_id:
            model = 'user.performance'
            person_field = 'user_id'
            person_id = self.user_id.id


        # Search for existing records with the same person, year, and any overlapping months
        domain = [
            (person_field, '=', person_id),
            ('year', '=', record.date_from.year),
        ]

        existing_records = self.env[model].search(domain)

        # Filter records that have overlapping months with the new selection
        selected_month_ids = set(self.month_ids.ids)

        records_to_update = self.env[model]

        for existing_record in existing_records:
            existing_month_ids = set(existing_record.month_ids.ids)

            if selected_month_ids & existing_month_ids:  # Check for intersection
                if selected_month_ids == existing_month_ids:
                    existing_record.write({
                        'achievement_level': self.achievement_level
                    })

            # Update the performance record lines as well

        performance_line = self.env['user.performance.record.line'].search([
            ('wizard_id', '=', record.id),
            ('name', '=', self.user_id.name),
            ('year', '=', record.date_from.year),
            ('month_ids', '=', self.month_ids.ids)
        ])
        if performance_line:
            performance_line.write({
                'achievement_level': self.achievement_level
            })

        datas = self.env['enquiry.performance.analysis'].search([])

        for data in datas:
            data.compute_performance_records()
            data._compute_achievement_level()
            data._compute_has_achievement()
        return {'type': 'ir.actions.act_window_close'}