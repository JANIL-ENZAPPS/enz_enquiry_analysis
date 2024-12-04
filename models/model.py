
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import calendar
from dateutil.relativedelta import relativedelta

class EnquiryPerformanceWizard(models.TransientModel):
    _name = 'enquiry.performance.wizard'
    _description = 'Enquiry Performance Analysis Wizard'


    filter_by = fields.Selection([
        ('user', 'User'),
        ('back_office_user', 'Back Office User')
    ], string="Filter By", required=True, default='user')

    report_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('custom', 'Custom Period')
    ], string='Report Type', default='quarterly', required=True)

    user_id = fields.Many2one('res.users', string='User',
                              domain="[('id', 'in', user_ids)]",
                              attrs="{'invisible': [('filter_by', '!=', 'user')]}")

    back_office_user_id = fields.Many2one('res.users', string='Back Office User',
                                          domain="[('id', 'in', back_office_user_ids)]",
                                          attrs="{'invisible': [('filter_by', '!=', 'back_office_user')]}")

    quarter = fields.Selection([
        ('q1', 'Q1'),
        ('q2', 'Q2'),
        ('q3', 'Q3'),
        ('q4', 'Q4')
    ], string='Quarter')

    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
        ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Month')

    year = fields.Selection([
        (str(year), str(year)) for year in range(datetime.now().year - 5, datetime.now().year + 1)
    ], string='Year', default=str(datetime.now().year))

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')

    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    branch_id = fields.Many2one('company.branches', string="Branch",
                                domain="[('company_id', '=', company_id)]")


    user_ids = fields.Many2many('res.users', compute='_compute_user_ids', store=False,
                                string="Available Users")

    back_office_user_ids = fields.Many2many('res.users', compute='_compute_back_office_user_ids', store=False,
                                            string="Available Back Office Users")

    @api.onchange('company_id', 'branch_id')
    def _compute_user_ids(self):
        for record in self:
            domain = []
            if record.company_id:
                domain.append(('company_id', '=', record.company_id.id))

            if record.branch_id:
                domain.append(('branch_id', '=', record.branch_id.id))

            users = self.env['enquiry.record'].search(domain).mapped('user_id')
            record.user_ids = [(6, 0, users.ids)]

    @api.onchange('company_id', 'branch_id')
    def _compute_back_office_user_ids(self):
        for record in self:
            domain = []
            if record.company_id:
                domain.append(('company_id', '=', record.company_id.id))

            if record.branch_id:
                domain.append(('branch_id', '=', record.branch_id.id))

            # Adjust this domain to match how you identify back office users in your system
            back_office_users = self.env['enquiry.record'].search(domain).mapped('back_office_user_id')
            record.back_office_user_ids = [(6, 0, back_office_users.ids)]

    @api.onchange('report_type')
    def _onchange_report_type(self):
        if self.report_type == 'quarterly':
            current_month = datetime.now().month
            self.quarter = f'q{(current_month - 1) // 3 + 1}'
            self.month = False
        elif self.report_type == 'monthly':
            self.quarter = False
            self.month = str(datetime.now().month)
        else:
            self.date_from = datetime.strptime(f"{self.year}-01-01", "%Y-%m-%d").date()
            self.date_to = fields.Date.today()
            self.quarter = False
            self.month = False

    def _get_date_range(self):
        if self.report_type == 'monthly':
            return f"{self.year}-{self.month.zfill(2)}-01", f"{self.year}-{self.month.zfill(2)}-{calendar.monthrange(int(self.year), int(self.month))[1]}"
        elif self.report_type == 'quarterly':
            quarters = {
                'q1': (f'{self.year}-01-01', f'{self.year}-03-31'),
                'q2': (f'{self.year}-04-01', f'{self.year}-06-30'),
                'q3': (f'{self.year}-07-01', f'{self.year}-09-30'),
                'q4': (f'{self.year}-10-01', f'{self.year}-12-31')
            }
            return quarters[self.quarter]
        return self.date_from, self.date_to
    def _get_sales_target(self, entity, entity_id):
            if entity == 'res.users' and entity_id:

                if self.report_type == 'monthly':
                    sales_target_user = self.env['sales.target.user.enquiry'].search([
                        ('user_id', '=', entity_id),
                        ('type', '=', 'month'),
                        ('month_period', '=', self.month),

                    ], limit=1)

                    if sales_target_user:

                        return sales_target_user.sales_target
                if self.report_type == 'quarterly':

                    sales_target_user = self.env['sales.target.user.enquiry'].search([
                        ('user_id', '=', entity_id),
                        ('type', '=', 'quarter'),
                        ('quarter', '=', self.quarter),
                    ], limit=1)

                    if sales_target_user:
                        return sales_target_user.sales_target
                if self.report_type == 'custom':
                    # Define quarters and corresponding months
                    quarters = {
                        'q1': ['1', '2', '3'],
                        'q2': ['4', '5', '6'],
                        'q3': ['7', '8', '9'],
                        'q4': ['10', '11', '12']
                    }

                    # Check if the custom date range covers the full year
                    if self.date_from.month == 1 and self.date_to.month == 12:
                        total_target = 0.0
                        for quarter in quarters.keys():
                            sales_target_quarter = self.env['sales.target.user.enquiry'].search([
                                ('user_id', '=', entity_id),
                                ('type', '=', 'quarter'),
                                ('quarter', '=', quarter),
                            ], limit=1)
                            if sales_target_quarter:
                                total_target += sales_target_quarter.sales_target
                        return total_target

            else:
                return 0
    def action_generate_report(self):
        date_from, date_to = self._get_date_range()

        # Create analysis records
        analysis_obj = self.env['enquiry.performance.analysis']
        analysis_obj.search([]).unlink()  # Clear previous records

        company_id = self.company_id.id if self.company_id else self.env.company.id
        branch_id = self.branch_id.id if self.branch_id else False
        if self.filter_by == 'user':
            if self.user_id:
                sales_target = self._get_sales_target('res.users', self.user_id.id)
                analysis = analysis_obj.create({
                    'user_id': self.user_id.id,
                    'date_from': date_from,
                    'date_to': date_to,
                    'company_id': company_id,
                    'branch_id':branch_id,
                    'user_ids': [(6, 0, self.user_ids.ids)],
                    'sales_target': sales_target,
                })
                performance_records = self.env['user.performance'].search([
                    ('user_id', '=', self.user_id.id),
                    ('year', '=', self.year)
                ])
                for record in performance_records:
                    self.env['user.performance.record.line'].create({
                        'wizard_id': analysis.id,
                        'name': record.user_id.name,
                        'month_ids': [(6, 0, record.month_ids.ids)],
                        'year': record.year,
                        'achievement_level': record.achievement_level,
                    })
            else :
                domain = [('company_id', '=', company_id)]
                if branch_id:
                    domain.append(('branch_id', '=', branch_id))
                users = self.env['enquiry.record'].search(domain).mapped('user_id')
                for user in users:
                    sales_target = self._get_sales_target('res.users', user.id)
                    analysis = analysis_obj.create({
                        'user_id': user.id,
                        'date_from': date_from,
                        'date_to': date_to,
                        'company_id': company_id,
                        'branch_id': branch_id if branch_id else False,
                        'user_ids': [(6, 0, self.user_ids.ids)],
                        'sales_target': sales_target,
                    })
                    performance_records = self.env['user.performance'].search([
                        ('user_id', '=', user.id),
                        ('year', '=', self.year)
                    ])
                    for record in performance_records:
                        self.env['user.performance.record.line'].create({
                            'wizard_id': analysis.id,
                            'name': user.name,
                            'month_ids': [(6, 0, record.month_ids.ids)],
                            'year': record.year,
                            'achievement_level': record.achievement_level,
                        })

        elif self.filter_by == 'back_office_user':
            if self.back_office_user_id:
                sales_target = self._get_sales_target('res.users', self.back_office_user_id.id)
                analysis = analysis_obj.create({
                    'user_id': self.back_office_user_id.id,
                    'date_from': date_from,
                    'date_to': date_to,
                    'company_id': company_id,
                    'branch_id': branch_id if branch_id else False,
                    'user_ids': [(6, 0, self.back_office_user_ids.ids)],
                    'sales_target': sales_target,
                })
                performance_records = self.env['user.performance'].search([
                    ('user_id', '=', self.back_office_user_id.id),
                    ('year', '=', self.year)
                ])
                for record in performance_records:
                    self.env['user.performance.record.line'].create({
                        'wizard_id': analysis.id,
                        'name': record.user_id.name,
                        'month_ids': [(6, 0, record.month_ids.ids)],
                        'year': record.year,
                        'achievement_level': record.achievement_level,
                    })
            else :
                domain = [('company_id', '=', company_id)]
                if branch_id:
                    domain.append(('branch_id', '=', branch_id))
                users = self.env['enquiry.record'].search(domain).mapped('back_office_user_id')
                for user in users:
                    sales_target = self._get_sales_target('res.users', user.id)
                    analysis = analysis_obj.create({
                        'user_id': user.id,
                        'date_from': date_from,
                        'date_to': date_to,
                        'company_id': company_id,
                        'branch_id': branch_id if branch_id else False,
                        'user_ids': [(6, 0, self.back_office_user_ids.ids)],
                        'sales_target': sales_target,
                    })
                    performance_records = self.env['user.performance'].search([
                        ('user_id', '=', user.id),
                        ('year', '=', self.year)
                    ])
                    for record in performance_records:
                        self.env['user.performance.record.line'].create({
                            'wizard_id': analysis.id,
                            'name': user.name,
                            'month_ids': [(6, 0, record.month_ids.ids)],
                            'year': record.year,
                            'achievement_level': record.achievement_level,
                        })
        return {
            'name': 'Enquiry Performance Dashboard',
            'type': 'ir.actions.act_window',
            'res_model': 'enquiry.performance.analysis',
            'view_mode': 'kanban,pivot,tree,graph',
            'target': 'current',
        }

class EnquiryPerformanceAnalysis(models.TransientModel):
    _name = 'enquiry.performance.analysis'
    _description = 'Enquiry Performance Analysis'

    user_id = fields.Many2one('res.users', string='User')
    name = fields.Char(related='user_id.name', string='Name')
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    image = fields.Binary(related='user_id.image_1920', string='Photo')
    branch_id = fields.Many2one('company.branches', string="Branch")
    user_ids = fields.Many2many('res.users',store=True,string="Available Users")




    # Key Performance Metrics
    total_enquiries = fields.Integer(string='Total Enquiries', compute='_compute_metrics', store=True)
    approved_enquiries = fields.Integer(string='Total Approved Enquiries', compute='_compute_metrics', store=True)
    cancelled_enquiries = fields.Integer(string='Cancelled Enquiries', compute='_compute_metrics', store=True)

    # Quotation Metrics
    total_quotations = fields.Integer(string='Total Quotations', compute='_compute_metrics', store=True)
    total_quotation_amount = fields.Float(string='Total Quotation Amount', compute='_compute_metrics', store=True)

    fastest_quot_to_so_time = fields.Float(string='Fastest Quotation to SO Time (Hours)', compute='_compute_metrics',
                                           store=True)
    fastest_quot_to_so_id = fields.Many2one('sale.order', string='Fastest Quoted SO', compute='_compute_metrics',
                                            store=True)

    # Sales Metrics
    total_sales = fields.Integer(string='Total Sales Orders', compute='_compute_metrics', store=True)
    total_sales_amount = fields.Float(string='Total Sales Amount', compute='_compute_metrics', store=True)
    #Purchase
    total_purchase = fields.Integer(string='Total Purchase Orders', compute='_compute_metrics', store=True)
    total_purchase_amount = fields.Float(string='Total Purchase Amount', compute='_compute_metrics', store=True)
    total_rfq = fields.Integer(string='Total Rfq count', compute='_compute_metrics', store=True)
    total_rfq_amount = fields.Float(string='Total Rfq Amount', compute='_compute_metrics', store=True)
    total_bills = fields.Float(string='Total Billed Amount', compute='_compute_metrics', store=True)
    # Invoice Metrics
    total_invoiced = fields.Float(string='Total Invoiced Amount', compute='_compute_metrics', store=True)
    fastest_so_to_invoice_time = fields.Float(string='Fastest SO to Invoice Time(Hours) ',
                                              compute='_compute_metrics', store=True)
    fastest_so_to_invoice_id = fields.Many2one('sale.order', string='Fastest Invoiced SO',
                                               compute='_compute_metrics', store=True)

    # Related Records Count
    new_customers_count = fields.Integer(string='New Customers', compute='_compute_metrics', store=True)
    new_products_count = fields.Integer(string='New Products', compute='_compute_metrics', store=True)

    total_invoice_profit = fields.Float(string='Total Invoice Profit', compute='_compute_metrics', store=True)
    ## System Vals
    # System Total Values
    total_enquiries_all = fields.Float('All Enquiries Sum', compute='_compute_sums', store=True)
    cancelled_enquiries_all = fields.Float('All Cancelled Enquiries Sum', compute='_compute_sums', store=True)
    approved_enquiries_all = fields.Float('All Approved Enquiries Sum', compute='_compute_sums', store=True)
    total_quotation_amount_all = fields.Float('All Quotation Sum', compute='_compute_sums', store=True)
    total_quotations_all = fields.Float('All Quotation Count', compute='_compute_sums', store=True)
    total_sales_all = fields.Float(string='All Sales Order Count', compute='_compute_sums', store=True)
    total_sales_amount_all = fields.Float(string='All Sales Amount', compute='_compute_sums', store=True)
    total_purchase_all = fields.Float(string='All Purchase Order Count', compute='_compute_sums', store=True)
    total_purchase_amount_all = fields.Float(string='All Purchase Amount', compute='_compute_sums', store=True)
    total_rfq_all = fields.Float(string='All RFQ Order Count', compute='_compute_sums', store=True)
    total_rfq_amount_all = fields.Float(string='All RFQ Amount', compute='_compute_sums', store=True)
    total_bills_all = fields.Float(string='All Bills Sum', compute='_compute_sums', store=True)
    total_invoiced_all = fields.Float(string='All Invoiced Sum', compute='_compute_sums', store=True)
    profit_all = fields.Float(string='All Profit Sum', compute='_compute_sums', store=True)
    customer_count_all = fields.Integer(string='Total New Customers', compute='_compute_sums', store=True)
    avg_approval_time_all = fields.Float(string='System Min Sale Approval Time', compute='_compute_sums', store=True)
    avg_invoice_time_all = fields.Float(string='System Min Invoice Time', compute='_compute_sums', store=True)
    new_product_sales_all = fields.Integer(string='Total New Products Sold', compute='_compute_sums', store=True)
    sales_target = fields.Integer(string='Sales Target', store=True)
    total_receipts_all = fields.Integer(string='Total Receipts', compute='_compute_sums', store=True)
    total_deliveries_all = fields.Integer(string='Total Deliveries', compute='_compute_sums', store=True)
    # Individual Score Fields
    enquiry_score = fields.Integer(string='Enquiry Score', compute='_compute_scores', store=True)
    enquiry_cancelled_score = fields.Integer(string='Enquiry Cancelled Score', compute='_compute_scores', store=True)
    enquiry_approved_score = fields.Integer(string='Enquiry Approved Score', compute='_compute_scores', store=True)
    sales_score = fields.Integer(string='Sales Score', compute='_compute_scores', store=True)
    invoice_score = fields.Integer(string='Invoice Score', compute='_compute_scores', store=True)
    profit_score = fields.Integer(string='Profit Score', compute='_compute_scores', store=True)
    quotation_score = fields.Integer(string='Quotation Score', compute='_compute_scores', store=True)
    customer_score = fields.Integer(string='New Customer Score', compute='_compute_scores', store=True)
    approval_time_score = fields.Integer(string='Approval Time Score', compute='_compute_scores', store=True)
    invoice_time_score = fields.Integer(string='Invoice Time Score', compute='_compute_scores', store=True)
    new_product_score = fields.Integer(string='New Product Score', compute='_compute_scores', store=True)
    rfq_score = fields.Integer(string='RFQ Score', compute='_compute_scores', store=True)
    purchase_score = fields.Integer(string='Purchase Score', compute='_compute_scores', store=True)
    bill_score = fields.Integer(string='Bill Score', compute='_compute_scores', store=True)
    total_score = fields.Integer(string='Total Score', compute='_compute_total_score', store=True)
    sales_target_score = fields.Integer(string='Sates Target Score', compute='_compute_total_score', store=True)
    #Percentage
    enquiry_percentage = fields.Float(string='Enquiry Percentage', compute='_compute_scores', store=True)
    enquiry_cancelled_percentage = fields.Float(string='Enquiry Cancelled Percentage', compute='_compute_scores',
                                                store=True)
    enquiry_approved_percentage = fields.Float(string='Enquiry Approved Percentage', compute='_compute_scores',
                                                store=True)
    sales_percentage = fields.Float(string='Sales Percentage', compute='_compute_scores', store=True)
    invoice_percentage = fields.Float(string='Invoice Percentage', compute='_compute_scores', store=True)
    profit_percentage = fields.Float(string='Profit Percentage', compute='_compute_scores', store=True)
    quotation_percentage = fields.Float(string='Quotation Percentage', compute='_compute_scores', store=True)
    customer_percentage = fields.Float(string='Customer Percentage', compute='_compute_scores', store=True)
    approval_time_percentage = fields.Float(string='Approval Time Percentage', compute='_compute_scores',
                                            store=True)
    invoice_time_percentage = fields.Float(string='Invoice Time Percentage', compute='_compute_scores', store=True)
    new_product_percentage = fields.Float(string='New Product Percentage', compute='_compute_scores', store=True)
    rfq_percentage = fields.Float(string='RFQ Percentage', compute='_compute_scores', store=True)
    purchase_percentage = fields.Float(string='Purchase Percentage', compute='_compute_scores', store=True)
    bill_percentage = fields.Float(string='Bill Percentage', compute='_compute_scores', store=True)
    sales_target_percentage = fields.Float(string='Sales Target Percentage', compute='_compute_scores', store=True)

    score_desc = fields.Char(compute='_compute_sales_score_desc', store=False, string="Score Calculation")
    score_config_ids = fields.Many2many('enquiry.range.config', string="Score Ranges",
                                        default=lambda self: self._default_score_config_ids())

    max_total_sales = fields.Float(string='Highest Total Sales', compute='_compute_badge', store=True,
                                   compute_sudo=True)
    max_quotations = fields.Float(string='Highest Quotations', compute='_compute_badge', store=True,
                                  compute_sudo=True)
    max_rfq = fields.Float(string='Highest RFQ', compute='_compute_badge', store=True,
                                  compute_sudo=True)
    max_purchase = fields.Float(string='Highest Purchase', compute='_compute_badge', store=True,
                                  compute_sudo=True)
    largest_value = fields.Float('Largest', compute='_compute_badge', store=True)

    # Add these to your model definition
    total_receipts = fields.Integer(string="Total Receipts")
    receipt_purchase_order_ids = fields.Many2many(
        'stock.picking',
        'receipt_purchase_order_move_rel',  # Unique relation table name
        'enquiry_id',  # Column for the current model
        'account_move_id',  # Column for the related model
        string="Receipt Purchase Orders"
    )
    total_deliveries = fields.Integer(string="Total Deliveries")
    delivery_sale_order_ids = fields.Many2many(
        'stock.picking',
        'delivery_sale_order_move_rel',  # Unique relation table name
        'enquiry_id',  # Column for the current model
        'account_move_id',  # Column for the related model
        string="Delivery Sale Orders"
    )
    filtered_enquiry_ids = fields.Many2many(
        'enquiry.record',
        string='Filtered Enquiries',
        readonly=True,
        help="Enquiries with bid close date time within the configured closing days.",
        compute="filter_enquiries"
    )
    filtered_enquiry_id_count = fields.Integer(string="Total Bid Close")

    def filter_enquiries(self):
        """
        Filters enquiries based on the bid_close_date_time and the configuration in bid.closing.days.config.
        """
        # Get the active bid closing days configuration
        config = self.env['bid.closing.days.config'].search([('active', '=', True)], limit=1)
        if config:
            threshold_datetime = datetime.now() + timedelta(days=config.bid_closing_days)
            enquiries = self.env['enquiry.record'].search([
                ('bid_close_date_time', '<=', threshold_datetime),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('user_id', '=', self.user_id.id)
            ])

            # Update the filtered_enquiry_ids field
            self.filtered_enquiry_ids = [(6, 0, enquiries.ids)]
            self.filtered_enquiry_id_count = len(enquiries)
        else:
            self.filtered_enquiry_ids = False
            self.filtered_enquiry_id_count = 0
    def _default_score_config_ids(self):
        # Fetch the desired score range configurations
        score_ranges = self.env['enquiry.range.config'].search([])  # Add any filtering logic here if needed
        return score_ranges

    @api.depends('sales_score')
    def _compute_sales_score_desc(self):
        for record in self:
            record.score_desc = (
                "Enquiry Score Calculation: \n"
                "1. Calculate the Sales Score using the formula: "
                "Sales Score = (Total Sales / System Total Sales) * 100. \n"
                "2. Based on the calculated Sales Score, assign points as follows:\n"
                "   - 0 - 10%: 1 point\n"
                "   - 11 - 20%: 2 points\n"
                "   - 21 - 30%: 3 points\n"
                "   - 31% and above: 4 points or more\n"
                "3. The Sales Score is intended to evaluate performance against the overall sales metrics."
            )

    medal = fields.Selection([
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('bronze', 'Bronze'),
        ('none', 'No Badge')
    ], string='Badge', compute='_compute_badge', store=True)

    badge_color = fields.Char(string='Badge Color', compute='_compute_badge', store=True)
    performance_record_lines = fields.One2many('user.performance.record.line', 'wizard_id',
                                               string='Performance Records')
    achievement_level = fields.Selection([
        ('superb', 'Superb Performer'),
        ('best', 'Best Performer'),
        ('good', 'Good Performer')
    ], string='Achievement Level', compute='_compute_achievement_level', store=True)

    has_achievement = fields.Boolean(string="Has Achievement", compute='_compute_has_achievement', store=True)

    def compute_performance_records(self):
        # Unlink existing performance record lines
        if self.performance_record_lines:
            self.performance_record_lines.unlink()

        if self.user_id:
            # Replace this with the appropriate employee domain
            performance_records = self.env['user.performance'].search([
                ('user_id', '=', self.user_id.id),
                # Ensure 'self.year' is defined in your model
            ])

            # Create new performance record lines
            for record in performance_records:
                self.env['user.performance.record.line'].create({

                    'wizard_id': self.id,  # Assign the current wizard ID
                    'name': self.user_id.name,
                    'month_ids': [(6, 0, record.month_ids.ids)],  # Use (6, 0, ids) for Many2many fields
                    'year': record.year,
                    'achievement_level': record.achievement_level,
                })


    @api.depends('date_from', 'date_to', 'performance_record_lines')
    def _compute_has_achievement(self):
        for record in self:
            has_achievement = False

            if record.date_from and record.date_to:
                # Get all months between date_from and date_to
                current_date = record.date_from
                selected_months = set()  # Using set for faster lookups
                while current_date <= record.date_to:
                    # Format month with year to match record_months format
                    month_name = f"{current_date.strftime('%B')} {current_date.year}"
                    selected_months.add(month_name)
                    current_date += relativedelta(months=1)

                # Check performance records for matching achievement level
                for line in record.performance_record_lines:
                    # Ensure the line's achievement level is set
                    if line.achievement_level:
                        # Get months from performance records including year
                        record_months = set(month.name for month in line.month_ids)

                        # If the record months fully match the selected period, mark as has_achievement
                        if selected_months <= record_months:
                            has_achievement = True
                            break

            # Set the boolean field based on whether any achievements were found
            record.has_achievement = has_achievement

    user_rankings_ids = fields.One2many(
        comodel_name='user.rankings',
        inverse_name='performance_analysis_id',
        string="User Rankings",
        help="List of all User ranked by score.",
        compute='_compute_user_rankings',
        store=True
    )

    @api.depends('total_score')
    def _compute_user_rankings(self):
        for rec in self:
            users = self.env['enquiry.performance.analysis'].search([], order='total_score desc')

            rankings = []
            for user in users:
                rankings.append(self.env['user.rankings'].create({
                    'performance_analysis_id': rec.id,
                    'user_id': user.user_id.id,
                    'score': user.total_score
                }))

    @api.depends('date_from', 'date_to', 'performance_record_lines', 'user_id')
    def _compute_achievement_level(self):
        for record in self:

            achievement = False
            if record.date_from and record.date_to and record.performance_record_lines:
                # Get all months between date_from and date_to
                current_date = record.date_from
                selected_months = set()  # Using set for faster lookups
                while current_date <= record.date_to:
                    # Format month with year to match record_months format
                    month_name = f"{current_date.strftime('%B')} {current_date.year}"
                    selected_months.add(month_name)
                    current_date += relativedelta(months=1)

                # Determine the entity name based on filter
                current_name = (record.user_id.name if record.user_id
                                else False)

                # Check performance records for matching achievement level
                for line in record.performance_record_lines:
                    if line.name == current_name and str(record.date_from.year) == line.year:
                        # Get months from performance records including year
                        record_months = set(month.name for month in line.month_ids)

                        # Check if the sets are equal
                        if selected_months == record_months:
                            achievement = line.achievement_level
                            break

            record.achievement_level = achievement

    ## Badge Fun
    @api.depends('total_score')
    def _compute_badge(self):
        for record in self:
            # Search for the badge configuration that matches the total score
            config = self.env['enquiry.badge.assignment.config'].search([
                ('min_score', '<=', record.total_score),
                ('max_score', '>=', record.total_score)
            ], limit=1)

            if config:
                record.medal = config.badge
                if config.badge == 'gold':
                    record.badge_color = '#FFD700'  # Gold color
                elif config.badge == 'silver':
                    record.badge_color = '#C0C0C0'  # Silver color
                elif config.badge == 'bronze':
                    record.badge_color = '#CD7F32'  # Bronze color
                else:
                    record.badge_color = '#808080'  # Grey for other badges
            else:
                record.medal = 'none'
                record.badge_color = '#808080'  # Default grey color when no badge is assigned

        all_records = self.search([])
        if all_records:
            self.max_total_sales = max(all_records.mapped('total_sales_amount'))
            self.max_quotations = max(all_records.mapped('total_quotation_amount'))
            self.max_rfq = max(all_records.mapped('total_rfq_amount'))
            self.max_purchase = max(all_records.mapped('total_purchase_amount'))
            # self.min_quotations = min(all_records.mapped('quotations'))
            # self.min_invoice = min(all_records.mapped('total_invoiced'))
            # self.min_profit = min(all_records.mapped('profit_level'))

            record.largest_value = max( record.max_total_sales, record.max_quotations ,record.max_rfq ,record.max_purchase)

            for rec in all_records:
                rec.largest_value = record.largest_value
            # record.lowest_value = min(record.min_total_sales, record.min_quotations, record.min_invoice)

            # Handle case where all values are equal
            # if record.largest_value == record.lowest_value:
            #     record.lowest_value = record.largest_value * 0.9  # Create a 10% padding below
        # else:
        #     self.max_total_sales = 0.0
        #     self.max_quotations = 0.0
        #     # self.min_total_sales = 0.0
        #     # self.min_quotations = 0.0
        #     record.largest_value = 1.0  # Default to avoid division by zero
        #     record.lowest_value = 0.0



    def _get_score_for_metric(self, metric_type, percentage):
        """Get score based on configuration ranges"""
        if percentage <= 0:
            return 0

        domain = [
            ('min_percentage', '<=', percentage),
            ('max_percentage', '>=', percentage),

        ]

        score_range = self.env['enquiry.range.config'].search(domain, limit=1)
        return score_range.points if score_range else 0

    @api.depends('total_sales_amount_all', 'total_invoiced_all', 'profit_all', 'total_quotation_amount_all',
                 'customer_count_all', 'avg_approval_time_all', 'avg_invoice_time_all',
                 'new_product_sales_all')
    def _compute_scores(self):
        for record in self:
            # Calculate percentages and get corresponding scores
            if record.total_enquiries and record.total_enquiries_all:
                record.enquiry_percentage = (record.total_enquiries / record.total_enquiries_all * 100)
                record.enquiry_score = record._get_score_for_metric('enquiry',record.enquiry_percentage)

            if record.approved_enquiries and record.approved_enquiries_all:
                record.enquiry_approved_percentage = (record.approved_enquiries / record.approved_enquiries_all * 100)
                record.enquiry_approved_score = record._get_score_for_metric('enquiry',record.enquiry_approved_percentage)


            if record.cancelled_enquiries and record.cancelled_enquiries_all:
                record.enquiry_cancelled_percentage = (record.cancelled_enquiries / record.cancelled_enquiries_all * 100)
                record.enquiry_cancelled_score = 0-(record._get_score_for_metric('enquiry', record.enquiry_cancelled_percentage))
            if record.total_sales_amount_all and record.total_sales_amount:
                record.sales_percentage = (record.total_sales_amount / record.total_sales_amount_all * 100)
                record.sales_score = record._get_score_for_metric('sales', record.sales_percentage)

            if record.total_invoiced and record.total_invoiced_all:
                record.invoice_percentage = (record.total_invoiced / record.total_invoiced_all * 100)
                record.invoice_score = record._get_score_for_metric('invoice', record.invoice_percentage)

            if record.total_purchase_amount_all and record.total_purchase_amount:
                record.purchase_percentage = (record.total_purchase_amount / record.total_purchase_amount_all * 100)
                record.purchase_score = record._get_score_for_metric('sales', record.purchase_percentage)

            if record.total_rfq_amount and record.total_rfq_amount_all:
                record.rfq_percentage = (record.total_rfq_amount / record.total_rfq_amount_all * 100)
                record.rfq_score = record._get_score_for_metric('invoice', record.rfq_percentage)

            if record.total_bills and record.total_bills_all:
                record.bill_percentage = (record.total_bills / record.total_bills_all * 100)
                record.bill_score = record._get_score_for_metric('invoice', record.bill_percentage)

            if record.profit_all and record.total_invoice_profit:
                record.profit_percentage = (record.total_invoice_profit / record.profit_all * 100)
                record.profit_score = record._get_score_for_metric('profit', record.profit_percentage)

            if record.total_quotation_amount_all and record.total_quotation_amount:
                record.quotation_percentage = (record.total_quotation_amount / record.total_quotation_amount_all * 100)
                record.quotation_score = record._get_score_for_metric('quotation', record.quotation_percentage)

            # if record.customer_count_all and record.new_customers_count:
            #     record.customer_percentage = (record.new_customers_count / record.customer_count_all * 100)
            #     record.customer_score = record._get_score_for_metric('customer', record.customer_percentage)
            #
            # if record.new_product_sales_all and record.new_products_count:
            #     record.new_product_percentage = (record.new_products_count / record.new_product_sales_all * 100)
            #     record.new_product_score = record._get_score_for_metric('new_product', record.new_product_percentage)

            # For time metrics (lower is better)
            if record.avg_approval_time_all and record.fastest_quot_to_so_time:
                record.approval_time_percentage = ((record.avg_approval_time_all / record.fastest_quot_to_so_time)) * 100
                record.approval_time_score = record._get_score_for_metric('approval_time', record.approval_time_percentage)

            if record.avg_invoice_time_all and record.fastest_so_to_invoice_time:
                record.invoice_time_percentage = ((record.avg_invoice_time_all / record.fastest_so_to_invoice_time)) * 100
                record.invoice_time_score = record._get_score_for_metric('invoice_time', record.invoice_time_percentage)

            if record.sales_target and record.total_sales_amount:
                record.sales_target_percentage = ((record.total_sales_amount / record.sales_target)) * 100
                record.sales_target_score = record._get_score_for_metric('invoice_time', record.sales_target_percentage)

    @api.depends(
        'sales_score', 'invoice_score', 'profit_score', 'quotation_score',
        'customer_score', 'approval_time_score', 'invoice_time_score', 'new_product_score','rfq_score','purchase_score'
    )
    def _compute_total_score(self):
        for record in self:
            record.total_score = sum([
                record.enquiry_score,
                record.enquiry_cancelled_score,
                record.sales_score,
                record.invoice_score,
                record.profit_score,
                record.quotation_score,
                record.approval_time_score,
                record.invoice_time_score,
                record.rfq_score,
                record.bill_score,
                record.purchase_score,
            ])


    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_sums(self):
        for record in self:

            # Get all related enquiries
            enquiries = self.env['enquiry.record'].search([])  # Adjust domain as needed
            enquiry_ids = enquiries.mapped('id')

            # Total enquiries
            record.total_enquiries_all = len(enquiries)

            # Cancelled enquiries
            cancelled = enquiries.filtered(lambda e: e.state == 'cancelled')
            approved = enquiries.filtered(lambda e: e.state == 'approved')
            record.cancelled_enquiries_all = len(cancelled)
            record.approved_enquiries_all = len(approved)

            domain_purchase = [
                ('company_id', '=', record.company_id.id),
                ('date_approve', '>=', record.date_from),
                ('date_approve', '<=', record.date_to),
                ('user_id', 'in', record.user_ids.ids)
            ]

            if record.branch_id:
                domain_purchase.append(('branch_id', '=', record.branch_id.id))

            purchase_orders = self.env['purchase.order'].search(domain_purchase + [
                ('state', 'in', ['purchase', 'done'])
            ])

            if purchase_orders:
                record.total_purchase_all = len(purchase_orders)

                # Calculate total purchase amount with currency conversion
                total_purchase_amount = 0
                for purchase in purchase_orders:
                    # Get the company's currency
                    company_currency = purchase.company_id.currency_id

                    # If the purchase order's currency is different from company currency, convert
                    if purchase.currency_id != company_currency:
                        # Convert amount to company currency
                        purchase_amount = purchase.currency_id._convert(
                            purchase.amount_total,
                            company_currency,
                            purchase.company_id,
                            purchase.date_order or fields.Date.today()
                        )
                    else:
                        purchase_amount = purchase.amount_total

                    total_purchase_amount += purchase_amount

                record.total_purchase_amount_all = total_purchase_amount

            # Similar modification for RFQ
            domain_purchase_rfq = [
                ('company_id', '=', record.company_id.id),
                ('date_order', '>=', record.date_from),
                ('date_order', '<=', record.date_to),
                ('user_id', 'in', record.user_ids.ids)
            ]
            rfq = self.env['purchase.order'].search(domain_purchase_rfq + [
                ('state', 'in', ['draft','sent'])
            ])
            if rfq:
                record.total_rfq_all = len(rfq)

                total_rfq_amount = 0
                for request in rfq:
                    company_currency = request.company_id.currency_id

                    if request.currency_id != company_currency:
                        # Convert amount to company currency
                        rfq_amount = request.currency_id._convert(
                            request.amount_total,
                            company_currency,
                            request.company_id,
                            request.date_order or fields.Date.today()
                        )
                    else:
                        rfq_amount = request.amount_total

                    total_rfq_amount += rfq_amount

                record.total_rfq_amount_all = total_rfq_amount

            bills = purchase_orders.mapped('invoice_ids').filtered(
                lambda inv: inv.move_type == 'in_invoice' and inv.state == 'posted')

            # Calculate total bill amount with currency conversion
            total_bills_amount = 0
            for bill in bills:
                company_currency = bill.company_id.currency_id

                if bill.currency_id != company_currency:
                    # Convert amount to company currency
                    bill_amount = bill.currency_id._convert(
                        bill.amount_total,
                        company_currency,
                        bill.company_id,
                        bill.invoice_date or fields.Date.today()
                    )
                else:
                    bill_amount = bill.amount_total

                total_bills_amount += bill_amount

            record.total_bills_all = total_bills_amount

            # Add receipt tracking

            receipts = self.env['stock.picking'].search([
                ('company_id', '=', record.company_id.id),
                ('picking_type_code', '=', 'incoming'),
                ('state', '=', 'done'),
                ('purchase_id', 'in', purchase_orders.ids)
            ])

            if receipts:
                record.total_receipts_all = len(receipts)

                # Collect receipt details
                receipt_details = []
                receipt_purchase_order_ids = []

                for receipt in receipts:

                    if receipt.purchase_id:
                        receipt_purchase_order_ids.append(receipt.id)



            ##Sales
            domain_sale = [
                ('company_id', '=', record.company_id.id),
                ('date_order', '>=', record.date_from),
                ('date_order', '<=', record.date_to),
                ('user_id', 'in', record.user_ids.ids)
            ]
            if record.branch_id:
                domain_sale.append(('branch_id', '=', record.branch_id.id))
            sales_orders = self.env['sale.order'].search(domain_sale + [
                ('state', 'in', ['sale', 'done'])
            ])
            if sales_orders:
                # Total Sales

                record.total_sales_all = len(sales_orders)
                record.total_sales_amount_all = sum(sales_orders.mapped('amount_total'))
            quotations = self.env['sale.order'].search(domain_sale + [
                ('state', 'not in', ['sale', 'done', 'cancel'])
            ])
            if quotations:
                # Quotation metrics
                record.total_quotations_all = len(quotations)
                record.total_quotation_amount_all = sum(quotations.mapped('amount_total'))

            # Invoice metrics
            invoices = sales_orders.mapped('invoice_ids').filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted')

            # Calculate total invoiced amount
            record.total_invoiced_all = sum(invoices.mapped('amount_total'))

            # Add delivery tracking
            deliveries = self.env['stock.picking'].search([
                ('company_id', '=', record.company_id.id),
                ('picking_type_code', '=', 'outgoing'),
                ('state', '=', 'done'),
                ('sale_id', 'in', sales_orders.ids)
            ])

            if deliveries:
                record.total_deliveries_all = len(deliveries)

                # Collect delivery details
                delivery_details = []
                delivery_sale_order_ids = []

                for delivery in deliveries:
                    if delivery.sale_id:
                        delivery_sale_order_ids.append(delivery.id)

            # Calculate profit using mapped
            total_profit = 0
            if invoices:
                for invoice in invoices:
                    for line in invoice.invoice_line_ids:
                        if line.product_id and line.quantity:
                            revenue = line.price_total  # Revenue from the line
                            cost = line.product_id.standard_price * line.quantity  # Cost of goods sold
                            profit = revenue - cost
                            # Add profit for regular invoices, subtract for credit notes
                            total_profit += profit if invoice.move_type == 'out_invoice' else -profit

            record.profit_all = total_profit

            # Count unique customers from confirmed sales
            record.customer_count_all = len(set(sales_orders.mapped('partner_id.id')))

            # Average approval time calculation (from enquiry to sale order confirmation)
            if sales_orders:
                approval_times = []
                fastest_quot_time = float('inf')
                fastest_quot_so = False
                for sale_order in sales_orders:
                    if sale_order.date_order and sale_order.create_date:
                        # Calculate time difference in hours
                        time_diff = (sale_order.date_order - sale_order.create_date).total_seconds() / 3600
                        if time_diff < fastest_quot_time:
                            fastest_quot_time = time_diff
                            fastest_quot_so = sale_order
                record.avg_approval_time_all = fastest_quot_time if fastest_quot_time else 0.0
            else:
                record.avg_approval_time_all = 0.0

            # Average invoice time calculation (from sale order confirmation to invoice)
            if invoices:
                fastest_invoice_time = float('inf')
                fastest_invoice_so = False
                invoice_times = []
                for invoice in invoices:
                    sale_order = sales_orders.filtered(lambda so: so.name == invoice.invoice_origin)
                    if sale_order and sale_order.date_order and invoice.invoice_date:
                        delta = fields.Datetime.from_string(invoice.invoice_date) - \
                                fields.Datetime.from_string(sale_order.date_order)
                        invoice_times.append(delta.total_seconds() / 3600)  # Convert to hours
                record.avg_invoice_time_all = min(invoice_times) if invoice_times else 0.0
            else:
                record.avg_invoice_time_all = 0.0

            start_of_month = fields.Date.today().replace(day=1)

            # Get all products in the order lines of confirmed sales
            sold_products = sales_orders.mapped('order_line.product_id')

            # Filter products created in the current month and get unique entries
            new_products_sold = sold_products.filtered(lambda p: p.create_date.date() >= start_of_month)
            record.new_product_sales_all = len(set(new_products_sold))

    @api.depends('user_id', 'date_from', 'date_to', 'company_id')
    def _compute_metrics(self):
        for record in self:
            domain = [
                ('company_id', '=', record.company_id.id),
                ('date', '>=', record.date_from),
                ('date', '<=', record.date_to),
                ('user_id', '=', record.user_id.id)
            ]
            if record.branch_id:
                domain.append(('branch_id', '=', record.branch_id.id))

            enquiries = self.env['enquiry.record'].search(domain)

            # Basic enquiry metrics
            record.total_enquiries = len(enquiries)
            record.cancelled_enquiries = len(enquiries.filtered(lambda e: e.state == 'cancel'))
            record.approved_enquiries = len(enquiries.filtered(lambda e: e.state == 'approved'))
            # Get all related Purchase orders

            domain_purchase = [
                ('company_id', '=', record.company_id.id),
                ('date_approve', '>=', record.date_from),
                ('date_approve', '<=', record.date_to),
                ('user_id', '=', record.user_id.id)
            ]
            if record.branch_id:
                domain_purchase.append(('branch_id', '=', record.branch_id.id))

            purchase_orders = self.env['purchase.order'].search(domain_purchase + [
                ('state', 'in', ['purchase', 'done'])
            ])

            if purchase_orders:
                record.total_purchase = len(purchase_orders)

                # Calculate total purchase amount with currency conversion
                total_purchase_amount = 0
                for purchase in purchase_orders:
                    # Get the company's currency
                    company_currency = purchase.company_id.currency_id

                    # If the purchase order's currency is different from company currency, convert
                    if purchase.currency_id != company_currency:
                        # Convert amount to company currency
                        purchase_amount = purchase.currency_id._convert(
                            purchase.amount_total,
                            company_currency,
                            purchase.company_id,
                            purchase.date_order or fields.Date.today()
                        )
                    else:
                        purchase_amount = purchase.amount_total

                    total_purchase_amount += purchase_amount

                record.total_purchase_amount = total_purchase_amount

            # Similar modification for RFQ
            domain_purchase_rfq = [
                ('company_id', '=', record.company_id.id),
                ('date_order', '>=', record.date_from),
                ('date_order', '<=', record.date_to),
                ('user_id', '=', record.user_id.id)
            ]
            if record.branch_id:
                domain_purchase_rfq.append(('branch_id', '=', record.branch_id.id))
            rfq = self.env['purchase.order'].search(domain_purchase_rfq + [
                ('state', 'in', ['draft', 'sent'])
            ])

            if rfq:
                record.total_rfq = len(rfq)

                total_rfq_amount = 0
                for request in rfq:
                    company_currency = request.company_id.currency_id

                    if request.currency_id != company_currency:
                        # Convert amount to company currency
                        rfq_amount = request.currency_id._convert(
                            request.amount_total,
                            company_currency,
                            request.company_id,
                            request.date_order or fields.Date.today()
                        )
                    else:
                        rfq_amount = request.amount_total


                    total_rfq_amount += rfq_amount

                record.total_rfq_amount = total_rfq_amount

            bills = purchase_orders.mapped('invoice_ids').filtered(
                lambda inv: inv.move_type == 'in_invoice' and inv.state == 'posted')

            # Calculate total bill amount with currency conversion
            total_bills_amount = 0
            for bill in bills:
                company_currency = bill.company_id.currency_id

                if bill.currency_id != company_currency:
                    # Convert amount to company currency
                    bill_amount = bill.currency_id._convert(
                        bill.amount_total,
                        company_currency,
                        bill.company_id,
                        bill.invoice_date or fields.Date.today()
                    )
                else:
                    bill_amount = bill.amount_total

                total_bills_amount += bill_amount

            record.total_bills = total_bills_amount

            # Add receipt tracking

            receipts = self.env['stock.picking'].search([
                ('company_id', '=', record.company_id.id),
                ('picking_type_code', '=', 'incoming'),
                ('state', '=', 'done'),
                ('purchase_id', 'in', purchase_orders.ids)
            ])

            if receipts:
                record.total_receipts = len(receipts)

                # Collect receipt details
                receipt_details = []
                receipt_purchase_order_ids = []

                for receipt in receipts:

                    if receipt.purchase_id:

                        receipt_purchase_order_ids.append(receipt.id)

                record.receipt_purchase_order_ids = [(6, 0, list(set(receipt_purchase_order_ids)))]

            ##Sales
            domain_sale = [
                ('company_id', '=', record.company_id.id),
                ('date_order', '>=', record.date_from),
                ('date_order', '<=', record.date_to),
                ('user_id', '=', record.user_id.id)
            ]
            if record.branch_id:
                domain_sale.append(('branch_id', '=', record.branch_id.id))
            sales_orders = self.env['sale.order'].search(domain_sale + [
                ('state', 'in', ['sale', 'done'])
            ])
            if sales_orders:
                # Total Sales

                record.total_sales = len(sales_orders)
                record.total_sales_amount = sum(sales_orders.mapped('amount_total'))
            quotations = self.env['sale.order'].search(domain_sale + [
                ('state', 'not in', ['sale', 'done','cancel'])
            ])
            if quotations:
            # Quotation metrics
                record.total_quotations = len(quotations)
                record.total_quotation_amount = sum(quotations.mapped('amount_total'))

            # Invoice metrics
            invoices = sales_orders.mapped('invoice_ids').filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted')

            # Calculate total invoiced amount
            record.total_invoiced = sum(invoices.mapped('amount_total'))

            # Add delivery tracking
            deliveries = self.env['stock.picking'].search([
                ('company_id', '=', record.company_id.id),
                ('picking_type_code', '=', 'outgoing'),
                ('state', '=', 'done'),
                ('sale_id', 'in', sales_orders.ids)
            ])

            if deliveries:
                record.total_deliveries = len(deliveries)

                # Collect delivery details
                delivery_details = []
                delivery_sale_order_ids = []

                for delivery in deliveries:
                    if delivery.sale_id:

                        delivery_sale_order_ids.append(delivery.id)

                record.delivery_sale_order_ids = [(6, 0, list(set(delivery_sale_order_ids)))]

            # Calculate total profit from invoices
            total_profit = 0
            if invoices:
                for invoice in invoices:
                    for line in invoice.invoice_line_ids:
                        if line.product_id and line.quantity:
                            revenue = line.price_total  # Revenue from the line
                            cost = line.product_id.standard_price * line.quantity  # Cost of goods sold
                            profit = revenue - cost
                            # Add profit for regular invoices, subtract for credit notes
                            total_profit += profit if invoice.move_type == 'out_invoice' else -profit
            record.total_invoice_profit = total_profit

            # Calculate fastest quotation to SO time
            fastest_quot_time = float('inf')
            fastest_quot_so = False
            for sale_order in sales_orders:
                if sale_order.date_order and sale_order.create_date:
                    # Calculate time difference in hours
                    time_diff = (sale_order.date_order - sale_order.create_date).total_seconds() / 3600
                    if time_diff < fastest_quot_time:
                        fastest_quot_time = time_diff
                        fastest_quot_so = sale_order

            # Set fastest quotation to SO time
            record.fastest_quot_to_so_time = fastest_quot_time if fastest_quot_time != float('inf') else 0.0
            record.fastest_quot_to_so_id = fastest_quot_so.id if fastest_quot_so else False

            # Calculate fastest SO to invoice time
            fastest_invoice_time = float('inf')
            fastest_invoice_so = False

            # Loop through confirmed sales orders
            for order in sales_orders:
                # Find related invoices for the order and ensure they are posted
                order_invoices = invoices.filtered(lambda inv: inv in order.invoice_ids and inv.state == 'posted')

                for invoice in order_invoices:
                    # Ensure both dates are datetime objects
                    order_date = order.date_order
                    invoice_date = datetime.combine(invoice.invoice_date,
                                                    datetime.min.time()) if invoice.invoice_date else None

                    # Calculate time difference between order date and invoice date in hours
                    if order_date and invoice_date:
                        time_diff = (invoice_date - order_date).total_seconds() / 3600
                        if time_diff < fastest_invoice_time:
                            fastest_invoice_time = time_diff
                            fastest_invoice_so = order

            # Set the fastest time and associated sales order
            record.fastest_so_to_invoice_time = fastest_invoice_time if fastest_invoice_time != float('inf') else 0.0
            record.fastest_so_to_invoice_id = fastest_invoice_so.id if fastest_invoice_so else False

            # Count new customers and products
            customers = sales_orders.mapped('partner_id')
            record.new_customers_count = len(customers.filtered(lambda c:
                                                                c.create_date and c.create_date.date() >= record.date_from
                                                                and c.create_date.date() <= record.date_to))

            products = self.env['product.product'].search([
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to),
                ('create_uid', '=', record.user_id.id)
            ])
            record.new_products_count = len(products)

    def action_view_total_enquiries(self):
        return {
            'name': 'Total Enquiries',
            'type': 'ir.actions.act_window',
            'res_model': 'enquiry.record',
            'view_mode': 'tree,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('user_id', '=', self.user_id.id)
            ],
            'context': {
                'create': False,
                'search_default_group_by_state': 1  # Group by state for better overview
            }
        }

    def action_view_approved_enquiries(self):
        return {
            'name': 'Approved Enquiries',
            'type': 'ir.actions.act_window',
            'res_model': 'enquiry.record',
            'view_mode': 'tree,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('user_id', '=', self.user_id.id),
                ('state', '=', 'approved')
            ],
            'context': {
                'create': False,
                'search_default_group_by_date': 1  # Group by date to see cancellation patterns
            }
        }

    def action_view_cancelled_enquiries(self):
        return {
            'name': 'Cancelled Enquiries',
            'type': 'ir.actions.act_window',
            'res_model': 'enquiry.record',
            'view_mode': 'tree,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('user_id', '=', self.user_id.id),
                ('state', '=', 'cancel')
            ],
            'context': {
                'create': False,
                'search_default_group_by_date': 1  # Group by date to see cancellation patterns
            }
        }
    def action_view_bid_close_enquiries(self):
        return {
            'name': 'Bid Closing Enquiries',
            'type': 'ir.actions.act_window',
            'res_model': 'enquiry.record',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.filtered_enquiry_ids.ids)],
            'context': {
                'create': False,

            }
        }


    def action_view_quotations(self):
        domain_base = [
            ('state', 'not in', ['sale', 'done','cancel']),
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]

        if self.user_id:
            domain_base.append(('user_id', '=', self.user_id.id))

        if self.branch_id:
            domain_base.append(('branch_id', '=', self.branch_id.id))
        return {
            'name': 'Quotations',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': domain_base,
            'context': {'create': False}
        }

    def action_view_sales_orders(self):
        domain_base = [
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]

        if self.user_id:
            domain_base.append(('user_id', '=', self.user_id.id))

        if self.branch_id:
            domain_base.append(('branch_id', '=', self.branch_id.id))
        return {
            'name': 'Quotations',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': domain_base,
            'context': {'create': False}
        }

    def action_view_invoices(self):
        domain_base = [
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]

        if self.user_id:
            domain_base.append(('user_id', '=', self.user_id.id))

        if self.branch_id:
            domain_base.append(('branch_id', '=', self.branch_id.id))

        sales_orders = self.env['sale.order'].search(domain_base + [
            ('state', 'in', ['sale', 'done'])
        ])

        # Collect all posted customer invoices linked to these sales orders
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('id', 'in', sales_orders.mapped('invoice_ids').filtered(lambda inv: inv.state == 'posted').ids)
        ])

        # Return action to display filtered invoices
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoices.ids)],
            'context': {'create': False}
        }

    def action_view_purchase_quotations(self):
        domain_base = [
            ('state', 'not in', ['purchase', 'done', 'cancel']),
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]

        if self.user_id:
            domain_base.append(('user_id', '=', self.user_id.id))

        if self.branch_id:
            domain_base.append(('branch_id', '=', self.branch_id.id))
        return {
            'name': 'RFQs',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': domain_base,
            'context': {'create': False}
        }

    def action_view_purchase_orders(self):
        domain_base = [
            ('state', 'in', ['purchase', 'done']),
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]

        if self.user_id:
            domain_base.append(('user_id', '=', self.user_id.id))

        if self.branch_id:
            domain_base.append(('branch_id', '=', self.branch_id.id))
        return {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': domain_base,
            'context': {'create': False}
        }

    def action_view_purchase_invoices(self):
        domain_base = [
            ('state', 'in', ['purchase', 'done']),
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]

        if self.user_id:
            domain_base.append(('user_id', '=', self.user_id.id))

        if self.branch_id:
            domain_base.append(('branch_id', '=', self.branch_id.id))

        purchase_orders = self.env['purchase.order'].search(domain_base + [
            ('state', 'in', ['purchase', 'done'])
        ])

        # Collect all posted customer invoices linked to these sales orders
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('id', 'in', purchase_orders.mapped('invoice_ids').filtered(lambda inv: inv.state == 'posted').ids)
        ])

        # Return action to display filtered invoices
        return {
            'name': 'Vendor Bills',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoices.ids)],
            'context': {'create': False}
        }
    def action_view_new_customers(self):
        return {
            'name': 'New Customers',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to),
                ('sale_order_ids.enquiry_rec_id.user_id', '=', self.user_id.id)
            ],
            'context': {'create': False}
        }

    def action_view_new_products(self):
        return {
            'name': 'New Products',
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'tree,form',
            'domain': [
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to),
                ('create_uid', '=', self.user_id.id)
            ],
            'context': {'create': False}
        }

    def action_view_fastest_quoted_so(self):
        if self.fastest_quot_to_so_id:
            return {
                'name': 'Fastest Quoted to SO',
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': self.fastest_quot_to_so_id.id,
                'target': 'current',
                'context': {'create': False}
            }
        return {'type': 'ir.actions.act_window_close'}

    def action_view_fastest_invoiced_so(self):
        if self.fastest_so_to_invoice_id:
            return {
                'name': 'Fastest SO to Invoice',
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': self.fastest_so_to_invoice_id.id,
                'target': 'current',
                'context': {'create': False}
            }
        return {'type': 'ir.actions.act_window_close'}

    def action_view_score_details(self):
        self.ensure_one()
        return {
            'name': 'Performance Score Details',
            'type': 'ir.actions.act_window',
            'res_model': 'enquiry.performance.analysis',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'flags': {'mode': 'readonly'},
            'context': {
                'default_id': self.id,
            }
        }
    def action_view_profit_level(self):
        enquiry_ids = self.env['enquiry.record'].search([
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('user_id', '=', self.user_id.id)
        ]).ids

        # Fetch relevant sales orders
        sales_orders = self.env['sale.order'].search([
            ('enquiry_rec_id', 'in', enquiry_ids),
            ('state', 'in', ['sale', 'done'])
        ])

        # Collect all posted customer invoices linked to these sales orders
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('id', 'in', sales_orders.mapped('invoice_ids').filtered(lambda inv: inv.state == 'posted').ids)
        ])

        # Return action to display filtered invoices
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoices.ids)],
            'context': {'create': False}
        }

    def action_view_receipts(self):
        """
        Action method to open a tree view of receipts associated with this record
        """
        self.ensure_one()

        # Get the purchase order IDs associated with receipts
        receipt_purchase_order_ids = self.receipt_purchase_order_ids.ids

        return {
            'name': _('Receipts'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [
                ('id', 'in', receipt_purchase_order_ids)
            ],
            'context': {
                'create': False,
                'delete': False,
            },
            'target': 'current',
        }

    def action_view_deliveries(self):
        """
        Action method to open a tree view of deliveries associated with this record
        """
        self.ensure_one()

        # Get the sale order IDs associated with deliveries
        delivery_sale_order_ids = self.delivery_sale_order_ids.ids

        return {
            'name': _('Deliveries'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [
                ('id', 'in', delivery_sale_order_ids)
            ],
            'context': {
                'create': False,
                'delete': False,
            },
            'target': 'current',
        }

    def action_open_form_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Enquiry Performance Analysis Form',
            'view_mode': 'form',
            'res_model': 'enquiry.performance.analysis',
            'res_id': self.id,
            'target': 'current',
        }
class UserPerformanceRecordLine(models.TransientModel):
    _name = 'user.performance.record.line'
    _description = 'User Performance Record Line'


    wizard_id = fields.Many2one('enquiry.performance.analysis', string='Wizard', ondelete='cascade')
    name = fields.Char(string='Name')
    month_ids = fields.Many2many('user.performance.month', string='Months', required=True)
    year = fields.Char(string='Year')
    achievement_level = fields.Selection([
        ('superb', 'Superb Performer'),
        ('best', 'Best Performer'),
        ('good', 'Good Performer')
    ], string='Achievement Level')



class UserRankings(models.TransientModel):
    _name = 'user.rankings'
    _description = 'User Rankings'

    performance_analysis_id = fields.Many2one(
        comodel_name='enquiry.performance.analysis',
        string="Performance Analysis"
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string="User"
    )
    score = fields.Float(string="Score")