from django.contrib import admin
from .models import GlobalSettings, CustomFieldDefinition


@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('General', {
            'fields': ('farm_name', 'start_date', 'currency_symbol')
        }),
        ('Financial Defaults', {
            'fields': ('default_milk_price_per_litre', 'default_inflation_rate_yearly',
                       'default_tax_rate_yearly', 'default_loan_interest_rate_yearly',
                       'default_depreciation_method')
        }),
        ('Operational Defaults', {
            'fields': ('default_lactation_period_days', 'default_dry_period_days',
                       'default_pregnancy_duration_days')
        }),
        ('Strategy & Thresholds', {
            'fields': ('feed_strategy_toggle', 'alert_vet_visit_overdue_days',
                       'alert_low_feed_inventory_threshold_kg', 'reinvestment_surplus_threshold')
        }),
    )

    def has_add_permission(self, request):
        # Only allow one instance of GlobalSettings
        return not GlobalSettings.objects.exists()


@admin.register(CustomFieldDefinition)
class CustomFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ('field_label', 'target_model', 'field_type', 'is_required')
    list_filter = ('target_model', 'field_type', 'is_required')
    search_fields = ('field_name', 'field_label')