from django import forms
from .models import Buffalo, Breed, LifecycleEvent, MilkProduction
from configuration.models import CustomFieldDefinition


class BreedForm(forms.ModelForm):
    class Meta:
        model = Breed
        fields = ['name', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class BuffaloForm(forms.ModelForm):
    class Meta:
        model = Buffalo
        fields = ['buffalo_id', 'name', 'breed', 'date_of_birth', 'gender',
                  'purchase_date', 'purchase_price', 'current_location',
                  'dam', 'sire', 'notes', 'image']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

        # Filter dam choices to only include female buffaloes
        self.fields['dam'].queryset = Buffalo.objects.filter(gender='FEMALE')

        # Filter sire choices to only include male buffaloes
        self.fields['sire'].queryset = Buffalo.objects.filter(gender='MALE')

        # Add custom fields if any
        custom_fields = CustomFieldDefinition.objects.filter(target_model='BUFFALO')

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
        custom_fields = CustomFieldDefinition.objects.filter(target_model='BUFFALO')

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


class LifecycleEventForm(forms.ModelForm):
    class Meta:
        model = LifecycleEvent
        fields = ['buffalo', 'event_type', 'event_date', 'notes', 'related_calf']
        widgets = {
            'event_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

        # Only show active buffaloes
        self.fields['buffalo'].queryset = Buffalo.objects.filter(is_active=True)

        # Initially hide related_calf field (will be shown via JavaScript when event_type is 'CALVING')
        self.fields['related_calf'].widget.attrs.update({'class': 'form-control', 'style': 'display:none;'})

    def clean(self):
        cleaned_data = super().clean()
        event_type = cleaned_data.get('event_type')
        buffalo = cleaned_data.get('buffalo')
        related_calf = cleaned_data.get('related_calf')

        # Validate for CALVING event
        if event_type == 'CALVING' and not related_calf:
            self.add_error('related_calf', 'A related calf must be specified for calving events')

        # Validate that only female buffaloes can have CALVING events
        if event_type == 'CALVING' and buffalo and buffalo.gender != 'FEMALE':
            self.add_error('buffalo', 'Only female buffaloes can have calving events')

        # Validate that only female buffaloes can have BRED or PREG_CONFIRMED events
        if event_type in ['BRED', 'PREG_CONFIRMED'] and buffalo and buffalo.gender != 'FEMALE':
            self.add_error('buffalo', 'Only female buffaloes can have breeding/pregnancy events')

        return cleaned_data


class MilkProductionForm(forms.ModelForm):
    class Meta:
        model = MilkProduction
        fields = ['buffalo', 'date', 'time_of_day', 'quantity_litres', 'somatic_cell_count', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

        # Only show active, milking buffaloes
        self.fields['buffalo'].queryset = Buffalo.objects.filter(is_active=True, status='MILKING')

    def clean(self):
        cleaned_data = super().clean()
        buffalo = cleaned_data.get('buffalo')

        # Validate that only MILKING buffaloes can have milk production records
        if buffalo and buffalo.status != 'MILKING':
            self.add_error('buffalo', 'Only milking buffaloes can have milk production records')

        return cleaned_data


class MilkProductionBatchForm(forms.Form):
    """Form for recording milk production for multiple buffaloes at once"""
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    time_of_day = forms.ChoiceField(choices=MilkProduction.TIME_CHOICES,
                                    widget=forms.Select(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get all active, milking buffaloes
        milking_buffaloes = Buffalo.objects.filter(is_active=True, status='MILKING')

        # Add a field for each buffalo
        for buffalo in milking_buffaloes:
            field_name = f"buffalo_{buffalo.id}_milk"
            self.fields[field_name] = forms.DecimalField(
                label=str(buffalo),
                required=False,
                min_value=0,
                decimal_places=2,
                widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Litres'})
            )