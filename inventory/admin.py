from django.contrib import admin
from .models import FodderType, FeedInventory, FeedPurchase, FeedConsumption, InHouseFeedProduction

@admin.register(FodderType)
class FodderTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'unit', 'current_cost_per_unit', 'is_produced_in_house')
    list_filter = ('category', 'is_produced_in_house')
    search_fields = ('name', 'description')

@admin.register(FeedInventory)
class FeedInventoryAdmin(admin.ModelAdmin):
    list_display = ('fodder_type', 'quantity_on_hand', 'last_updated')
    search_fields = ('fodder_type__name',)

@admin.register(FeedPurchase)
class FeedPurchaseAdmin(admin.ModelAdmin):
    list_display = ('date', 'fodder_type', 'quantity_purchased', 'cost_per_unit', 'total_cost', 'supplier')
    list_filter = ('fodder_type', 'date')
    search_fields = ('fodder_type__name', 'supplier')
    date_hierarchy = 'date'

@admin.register(FeedConsumption)
class FeedConsumptionAdmin(admin.ModelAdmin):
    list_display = ('date', 'fodder_type', 'quantity_consumed', 'consumed_by', 'buffalo')
    list_filter = ('fodder_type', 'date', 'consumed_by')
    search_fields = ('fodder_type__name', 'group_name')
    date_hierarchy = 'date'
    autocomplete_fields = ['buffalo']

@admin.register(InHouseFeedProduction)
class InHouseFeedProductionAdmin(admin.ModelAdmin):
    list_display = ('date', 'fodder_type', 'quantity_produced', 'total_production_cost', 'cost_per_unit')
    list_filter = ('fodder_type', 'date')
    search_fields = ('fodder_type__name',)
    date_hierarchy = 'date'