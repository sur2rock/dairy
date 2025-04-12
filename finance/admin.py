from django.contrib import admin
from .models import ExpenseCategory, IncomeCategory, ExpenseRecord, IncomeRecord, Profitability

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_direct_cost', 'description')
    list_filter = ('is_direct_cost',)
    search_fields = ('name',)

@admin.register(IncomeCategory)
class IncomeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(ExpenseRecord)
class ExpenseRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'category', 'description', 'amount', 'supplier_vendor', 'related_buffalo')
    list_filter = ('category', 'date')
    search_fields = ('description', 'supplier_vendor')
    date_hierarchy = 'date'
    autocomplete_fields = ['related_buffalo']

@admin.register(IncomeRecord)
class IncomeRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'category', 'description', 'quantity', 'unit_price', 'total_amount', 'customer', 'related_buffalo')
    list_filter = ('category', 'date')
    search_fields = ('description', 'customer')
    date_hierarchy = 'date'
    autocomplete_fields = ['related_buffalo']

@admin.register(Profitability)
class ProfitabilityAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'total_income', 'direct_costs', 'indirect_costs', 'gross_profit', 'net_profit')
    list_filter = ('year',)
    date_hierarchy = 'calculated_at'
    readonly_fields = ('calculated_at',)