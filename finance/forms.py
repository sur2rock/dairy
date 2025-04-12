from django import forms
from .models import ExpenseRecord, IncomeRecord, ExpenseCategory, IncomeCategory
from configuration.models import CustomFieldDefinition, GlobalSettings
from herd.models import Buffalo


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description', 'is_direct_cost']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

        # Checkbox field needs special handling
        self.fields['is_direct_cost'].widget.attrs.update({'class': 'form-check-input'})


class IncomeCategoryForm(forms.ModelForm):
    class Meta:
        model = IncomeCategory
        fields = ['name', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class ExpenseRecordForm(forms.ModelForm):
    class Meta:
        model = ExpenseRecord
        fields = ['date', 'category', 'description', 'amount', 'related_buffalo',
                  'supplier_vendor', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

        # Only show active buffaloes in dropdown
        self.fields['related_buffalo'].queryset = Buffalo.objects.filter(is_active=True)

        # Add custom fields if any
        custom_fields = CustomFieldDefinition.objects.filter(target_model='EXPENSE')

        for cf in custom_fields:
            field_name = f"custom_{cf.field_name}"

            # Get initial value if this is an edit form
            initial_value = None
            if self.instance.pk and cf.field_name in self.instance.custom_data:
                initial_value = self.instance.custom_data[cf.field_name]

            # Create appropriate field based on type
            if cf.field_type == 'TEXT':
                self.fields[field_name] = forms.CharField(
                    label=cf.field_label,
                    required=cf.is_required,
                    initial=initial_value,
                    widget=forms.TextInput(attrs={'class': 'form-control'})
                )
            elif cf.field_type == 'NUMBER':
                self.fields[field_name] = forms.DecimalField(
                    label=cf.field_label,
                    required=cf.is_required,
                    initial=initial_value,
                    widget=forms.NumberInput(attrs={'class': 'form-control'})
                )
            elif cf.field_type == 'DATE':
                self.fields[field_name] = forms.DateField(
                    label=cf.field_label,
                    required=cf.is_required,
                    initial=initial_value,
                    widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
                )
            elif cf.field_type == 'BOOLEAN':
                self.fields[field_name] = forms.BooleanField(
                    label=cf.field_label,
                    required=cf.is_required,
                    initial=initial_value,
                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                )

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Save custom fields to custom_data JSON field
        custom_fields = CustomFieldDefinition.objects.filter(target_model='EXPENSE')

        for cf in custom_fields:
            field_name = f"custom_{cf.field_name}"
            if field_name in self.cleaned_data:
                # Convert date objects to strings for JSON storage
                value = self.cleaned_data[field_name]
                if isinstance(value, (forms.fields.datetime.date, forms.fields.datetime.datetime)):
                    value = value.isoformat()

                # Update the custom_data dictionary
                instance.custom_data[cf.field_name] = value

        if commit:
            instance.save()

        return instance


class IncomeRecordForm(forms.ModelForm):
    class Meta:
        model = IncomeRecord
        fields = ['date', 'category', 'description', 'quantity', 'unit_price', 'total_amount',
                  'related_buffalo', 'customer', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

        # Only show active buffaloes in dropdown
        self.fields['related_buffalo'].queryset = Buffalo.objects.filter(is_active=True)

        # Get default milk price from settings for initial value
        settings = GlobalSettings.objects.first()
        if settings and not self.instance.pk:  # Only for new records
            self.fields['unit_price'].initial = settings.default_milk_price_per_litre

        # Add custom fields if any
        custom_fields = CustomFieldDefinition.objects.filter(target_model='INCOME')

        for cf in custom_fields:
            field_name = f"custom_{cf.field_name}"

            # Get initial value if this is an edit form
            initial_value = None
            if self.instance.pk and cf.field_name in self.instance.custom_data:
                initial_value = self.instance.custom_data[cf.field_name]

            # Create appropriate field based on type
            if cf.field_type == 'TEXT':
                self.fields[field_name] = forms.CharField(
                    label=cf.field_label,
                    required=cf.is_required,
                    initial=initial_value,
                    widget=forms.TextInput(attrs={'class': 'form-control'})
                )
            elif cf.field_type == 'NUMBER':
                self.fields[field_name] = forms.DecimalField(
                    label=cf.field_label,
                    required=cf.is_required,
                    initial=initial_value,
                    widget=forms.NumberInput(attrs={'class': 'form-control'})
                )
            elif cf.field_type == 'DATE':
                self.fields[field_name] = forms.DateField(
                    label=cf.field_label,
                    required=cf.is_required,
                    initial=initial_value,
                    widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
                )
            elif cf.field_type == 'BOOLEAN':
                self.fields[field_name] = forms.BooleanField(
                    label=cf.field_label,
                    required=cf.is_required,
                    initial=initial_value,
                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                )

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')
        total_amount = cleaned_data.get('total_amount')

        # If quantity and unit_price are provided but total_amount is not, calculate it
        if quantity and unit_price and not total_amount:
            cleaned_data['total_amount'] = quantity * unit_price

        # Ensure total_amount is provided if quantity or unit_price is missing
        if not total_amount and (not quantity or not unit_price):
            self.add_error('total_amount', 'Please provide either Total Amount or both Quantity and Unit Price')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # If quantity and unit_price are provided but total_amount is not, calculate it
        if self.cleaned_data.get('quantity') and self.cleaned_data.get('unit_price') and not self.cleaned_data.get(
                'total_amount'):
            instance.total_amount = self.cleaned_data['quantity'] * self.cleaned_data['unit_price']

        # Save custom fields to custom_data JSON field
        custom_fields = CustomFieldDefinition.objects.filter(target_model='INCOME')

        for cf in custom_fields:
            field_name = f"custom_{cf.field_name}"
            if field_name in self.cleaned_data:
                # Convert date objects to strings for JSON storage
                value = self.cleaned_data[field_name]
                if isinstance(value, (forms.fields.datetime.date, forms.fields.datetime.datetime)):
                    value = value.isoformat()

                # Update the custom_data dictionary
                instance.custom_data[cf.field_name] = value

        if commit:
            instance.save()

        return instance


class MilkIncomeGeneratorForm(forms.Form):
    """Form for auto-generating milk income from production records"""
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    milk_price = forms.DecimalField(
        min_value=0.01,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    customer = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default milk price from settings
        settings = GlobalSettings.objects.first()
        if settings:
            self.fields['milk_price'].initial = settings.default_milk_price_per_litre