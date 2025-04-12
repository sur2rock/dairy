from django.db import models


class GlobalSettings(models.Model):
    """Central configuration settings for the entire farm"""
    farm_name = models.CharField(max_length=100)
    start_date = models.DateField()
    currency_symbol = models.CharField(max_length=5, default="$")

    # Financial defaults
    default_milk_price_per_litre = models.DecimalField(max_digits=10, decimal_places=2)
    default_inflation_rate_yearly = models.DecimalField(max_digits=5, decimal_places=2, default=3.00)
    default_tax_rate_yearly = models.DecimalField(max_digits=5, decimal_places=2, default=15.00)
    default_loan_interest_rate_yearly = models.DecimalField(max_digits=5, decimal_places=2, default=8.00)
    default_depreciation_method = models.CharField(
        max_length=3,
        choices=[('SLM', 'Straight Line Method'), ('WDV', 'Written Down Value')],
        default='SLM'
    )

    # Operational defaults
    default_lactation_period_days = models.PositiveIntegerField(default=305)
    default_dry_period_days = models.PositiveIntegerField(default=60)
    default_pregnancy_duration_days = models.PositiveIntegerField(default=280)

    # Feed strategy
    feed_strategy_toggle = models.CharField(
        max_length=20,
        choices=[('BUY_ALL', 'Buy All'), ('IN_HOUSE_PRIORITY', 'In-House Priority')],
        default='BUY_ALL'
    )

    # Alert thresholds
    alert_vet_visit_overdue_days = models.PositiveIntegerField(default=7)
    alert_low_feed_inventory_threshold_kg = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    reinvestment_surplus_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=10000.00)

    # Update timestamp
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.farm_name} Settings"

    class Meta:
        verbose_name = "Global Settings"
        verbose_name_plural = "Global Settings"


class CustomFieldDefinition(models.Model):
    """Defines custom fields that can be added to specific modules"""
    FIELD_TYPES = [
        ('TEXT', 'Text'),
        ('NUMBER', 'Number'),
        ('DATE', 'Date'),
        ('BOOLEAN', 'Boolean'),
    ]

    TARGET_MODELS = [
        ('BUFFALO', 'Buffalo'),
        ('EXPENSE', 'Expense'),
        ('INCOME', 'Income'),
        ('EMPLOYEE', 'Employee'),
    ]

    target_model = models.CharField(max_length=20, choices=TARGET_MODELS)
    field_name = models.CharField(max_length=50)
    field_label = models.CharField(max_length=100)
    field_type = models.CharField(max_length=10, choices=FIELD_TYPES)
    is_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.field_label} ({self.get_target_model_display()})"

    class Meta:
        unique_together = ('target_model', 'field_name')