from django.contrib import admin
from .models import Buffalo, Breed, LifecycleEvent, MilkProduction

@admin.register(Breed)
class BreedAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Buffalo)
class BuffaloAdmin(admin.ModelAdmin):
    list_display = ('buffalo_id', 'name', 'breed', 'gender', 'status', 'date_of_birth', 'is_active')
    list_filter = ('status', 'breed', 'gender', 'is_active')
    search_fields = ('buffalo_id', 'name')
    date_hierarchy = 'date_of_birth'
    readonly_fields = ('cumulative_cost', 'lactation_number')
    fieldsets = (
        ('Basic Information', {
            'fields': ('buffalo_id', 'name', 'breed', 'gender', 'date_of_birth', 'image')
        }),
        ('Status & Location', {
            'fields': ('status', 'current_location', 'is_active')
        }),
        ('Acquisition', {
            'fields': ('purchase_date', 'purchase_price')
        }),
        ('Family & Reproduction', {
            'fields': ('dam', 'sire', 'date_last_calved', 'date_due', 'expected_dry_off_date', 'lactation_number')
        }),
        ('Financial', {
            'fields': ('cumulative_cost',)
        }),
        ('Additional Information', {'fields': ('custom_data', 'notes')
        }),
    )

@admin.register(LifecycleEvent)
class LifecycleEventAdmin(admin.ModelAdmin):
    list_display = ('buffalo', 'event_type', 'event_date', 'get_related_calf_display')
    list_filter = ('event_type', 'event_date')
    search_fields = ('buffalo__buffalo_id', 'buffalo__name', 'notes')
    date_hierarchy = 'event_date'

    def get_related_calf_display(self, obj):
        if obj.related_calf:
            return obj.related_calf.buffalo_id
        return None

    get_related_calf_display.short_description = 'Related Calf'

@admin.register(MilkProduction)
class MilkProductionAdmin(admin.ModelAdmin):
    list_display = ('buffalo', 'date', 'time_of_day', 'quantity_litres', 'somatic_cell_count')
    list_filter = ('date', 'time_of_day')
    search_fields = ('buffalo__buffalo_id', 'buffalo__name')
    date_hierarchy = 'date'