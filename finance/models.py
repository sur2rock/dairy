from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

from herd.models import Buffalo


class ExpenseCategory(models.Model):
    """Categories for expense classification"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_direct_cost = models.BooleanField(default=True,
                                         help_text="Direct costs are included in Gross Profit calculation")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Expense Categories"


class IncomeCategory(models.Model):
    """Categories for income classification"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Income Categories"


class ExpenseRecord(models.Model):
    """Records for tracking all expenses"""
    date = models.DateField()
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Optional relationships
    related_buffalo = models.ForeignKey(Buffalo, on_delete=models.SET_NULL, blank=True, null=True,
                                        related_name='expenses')
    related_module = models.CharField(max_length=50, blank=True, null=True,
                                      help_text="Module that generated this expense (e.g., FeedPurchase, Payroll)")
    related_record_id = models.IntegerField(blank=True, null=True,
                                            help_text="ID of the record in the related module")

    # Vendor/supplier information
    supplier_vendor = models.CharField(max_length=100, blank=True, null=True)

    # Additional information
    notes = models.TextField(blank=True, null=True)

    # Custom fields (stored as JSON)
    custom_data = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date} - {self.category}: {self.amount}"

    class Meta:
        ordering = ['-date', '-created_at']


class IncomeRecord(models.Model):
    """Records for tracking all income"""
    date = models.DateField()
    category = models.ForeignKey(IncomeCategory, on_delete=models.PROTECT)
    description = models.CharField(max_length=255)

    # Optional quantity and unit price fields
    quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                   help_text="E.g., Litres for milk, Head for calves")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                     help_text="Price per unit")

    # Required total amount
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Optional relationships
    related_buffalo = models.ForeignKey(Buffalo, on_delete=models.SET_NULL, blank=True, null=True,
                                        related_name='income')

    # Customer information
    customer = models.CharField(max_length=100, blank=True, null=True)

    # Additional information
    notes = models.TextField(blank=True, null=True)

    # Custom fields (stored as JSON)
    custom_data = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date} - {self.category}: {self.total_amount}"

    def save(self, *args, **kwargs):
        # If quantity and unit_price are provided but total_amount is not, calculate it
        if self.quantity and self.unit_price and not self.total_amount:
            self.total_amount = self.quantity * self.unit_price

        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-date', '-created_at']


class Profitability(models.Model):
    """Monthly summary of financial metrics"""
    year = models.IntegerField()
    month = models.IntegerField()
    total_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    direct_costs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    indirect_costs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    roi_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    cash_surplus = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    calculated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.year}-{self.month:02d} Profitability"

    class Meta:
        unique_together = ['year', 'month']
        ordering = ['-year', '-month']
        verbose_name_plural = "Profitability Records"