from django import forms
from .models import FodderType, FeedInventory, FeedPurchase, FeedConsumption, InHouseFeedProduction
from herd.models import Buffalo


class FodderTypeForm(forms.ModelForm):
    class Meta:
        model = FodderType
        fields = ['name', 'description', 'unit', 'category', 'current_cost_per_unit',
                  'nutrient_info', 'is_produced_in_house']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

        # Checkbox field needs special handling
        self.fields['is_produced_in_house'].widget.attrs.update({'class': 'form-check-input'})


class FeedInventoryForm(forms.ModelForm):
    class Meta:
        model = FeedInventory
        fields = ['fodder_type', 'quantity_on_hand']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class FeedPurchaseForm(forms.ModelForm):
    class Meta:
        model = FeedPurchase
        fields = ['fodder_type', 'date', 'supplier', 'quantity_purchased',
                  'cost_per_unit', 'total_cost', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

        # Make total_cost not required, as it will be calculated
        self.fields['total_cost'].required = False

    def clean(self):
        cleaned_data = super().clean()
        quantity_purchased = cleaned_data.get('quantity_purchased')
        cost_per_unit = cleaned_data.get('cost_per_unit')
        total_cost = cleaned_data.get('total_cost')

        # If quantity and cost_per_unit are provided but total_cost is not, calculate it
        if quantity_purchased and cost_per_unit and not total_cost:
            cleaned_data['total_cost'] = quantity_purchased * cost_per_unit

        # Ensure total_cost is provided if quantity or cost_per_unit is missing
        if not total_cost and (not quantity_purchased or not cost_per_unit):
            self.add_error('total_cost', 'Please provide either Total Cost or both Quantity and Cost Per Unit')

        return cleaned_data


class FeedConsumptionForm(forms.ModelForm):
    class Meta:
        model = FeedConsumption
        fields = ['fodder_type', 'date', 'quantity_consumed', 'consumed_by',
                  'group_name', 'buffalo', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

        # Only show active buffaloes in dropdown
        self.fields['buffalo'].queryset = Buffalo.objects.filter(is_active=True)

        # Initially hide these fields (they will be shown/hidden via JavaScript based on consumed_by)
        self.fields['group_name'].widget.attrs.update({'style': 'display:none;'})
        self.fields['buffalo'].widget.attrs.update({'style': 'display:none;'})

    def clean(self):
        cleaned_data = super().clean()
        consumed_by = cleaned_data.get('consumed_by')
        group_name = cleaned_data.get('group_name')
        buffalo = cleaned_data.get('buffalo')

        if consumed_by == 'GROUP' and not group_name:
            self.add_error('group_name', 'Group name is required when consuming by a specific group')

        if consumed_by == 'INDIVIDUAL' and not buffalo:
            self.add_error('buffalo', 'Buffalo is required when consuming by an individual buffalo')

        return cleaned_data


class InHouseFeedProductionForm(forms.ModelForm):
    class Meta:
        model = InHouseFeedProduction
        fields = ['fodder_type', 'date', 'quantity_produced', 'seed_cost',
                  'fertilizer_cost', 'labor_cost', 'machinery_cost', 'other_costs', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

        # Only show fodder types that are marked as in-house produced
        self.fields['fodder_type'].queryset = FodderType.objects.filter(is_produced_in_house=True)