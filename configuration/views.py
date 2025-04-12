from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from .models import GlobalSettings, CustomFieldDefinition
from .serializers import GlobalSettingsSerializer, CustomFieldDefinitionSerializer


def is_admin(user):
    return user.is_superuser or user.is_staff


@login_required
@user_passes_test(is_admin)
def settings_view(request):
    """View for managing global settings"""
    settings = GlobalSettings.objects.first()

    if request.method == 'POST':
        # Simple form validation and saving
        try:
            farm_name = request.POST.get('farm_name')
            start_date = request.POST.get('start_date')
            currency_symbol = request.POST.get('currency_symbol')
            default_milk_price = request.POST.get('default_milk_price_per_litre')
            # ... get all other fields from the form

            if not settings:
                settings = GlobalSettings()

            settings.farm_name = farm_name
            settings.start_date = start_date
            settings.currency_symbol = currency_symbol
            settings.default_milk_price_per_litre = default_milk_price
            # ... set all other fields

            settings.save()
            messages.success(request, 'Settings updated successfully!')
            return redirect('configuration:settings')
        except Exception as e:
            messages.error(request, f'Error saving settings: {str(e)}')

    context = {
        'title': 'Global Settings',
        'settings': settings
    }
    return render(request, 'dairy_erp/configuration/settings.html', context)


@login_required
@user_passes_test(is_admin)
def custom_fields_view(request):
    """View for managing custom fields"""
    custom_fields = CustomFieldDefinition.objects.all().order_by('target_model', 'field_label')

    context = {
        'title': 'Custom Fields',
        'custom_fields': custom_fields
    }
    return render(request, 'dairy_erp/configuration/custom_fields.html', context)


@login_required
@user_passes_test(is_admin)
def add_custom_field(request):
    """View for adding a new custom field"""
    if request.method == 'POST':
        try:
            target_model = request.POST.get('target_model')
            field_name = request.POST.get('field_name')
            field_label = request.POST.get('field_label')
            field_type = request.POST.get('field_type')
            is_required = request.POST.get('is_required') == 'on'

            # Validate field_name format (no spaces, only alphanumeric and underscore)
            if not field_name.isalnum() and '_' not in field_name:
                raise ValueError("Field name must contain only letters, numbers, and underscores")

            # Check for duplicates
            if CustomFieldDefinition.objects.filter(target_model=target_model, field_name=field_name).exists():
                raise ValueError("A field with this name already exists for the selected model")

            custom_field = CustomFieldDefinition(
                target_model=target_model,
                field_name=field_name,
                field_label=field_label,
                field_type=field_type,
                is_required=is_required
            )
            custom_field.save()

            messages.success(request, 'Custom field added successfully!')
            return redirect('configuration:custom_fields')
        except Exception as e:
            messages.error(request, f'Error adding custom field: {str(e)}')

    context = {
        'title': 'Add Custom Field',
        'target_models': CustomFieldDefinition.TARGET_MODELS,
        'field_types': CustomFieldDefinition.FIELD_TYPES
    }
    return render(request, 'dairy_erp/configuration/add_custom_field.html', context)


@login_required
@user_passes_test(is_admin)
def edit_custom_field(request, field_id):
    """View for editing an existing custom field"""
    custom_field = get_object_or_404(CustomFieldDefinition, id=field_id)

    if request.method == 'POST':
        try:
            field_label = request.POST.get('field_label')
            is_required = request.POST.get('is_required') == 'on'

            custom_field.field_label = field_label
            custom_field.is_required = is_required
            custom_field.save()

            messages.success(request, 'Custom field updated successfully!')
            return redirect('configuration:custom_fields')
        except Exception as e:
            messages.error(request, f'Error updating custom field: {str(e)}')

    context = {
        'title': 'Edit Custom Field',
        'custom_field': custom_field
    }
    return render(request, 'dairy_erp/configuration/edit_custom_field.html', context)


@login_required
@user_passes_test(is_admin)
def delete_custom_field(request, field_id):
    """View for deleting a custom field"""
    custom_field = get_object_or_404(CustomFieldDefinition, id=field_id)

    if request.method == 'POST':
        try:
            custom_field.delete()
            messages.success(request, 'Custom field deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting custom field: {str(e)}')

    return redirect('configuration:custom_fields')


# API ViewSets
class GlobalSettingsViewSet(viewsets.ModelViewSet):
    """API endpoint for GlobalSettings"""
    queryset = GlobalSettings.objects.all()
    serializer_class = GlobalSettingsSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        # Only return the first (and only) settings object
        return GlobalSettings.objects.all()[:1]


class CustomFieldDefinitionViewSet(viewsets.ModelViewSet):
    """API endpoint for CustomFieldDefinition"""
    queryset = CustomFieldDefinition.objects.all()
    serializer_class = CustomFieldDefinitionSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['target_model', 'field_type', 'is_required']