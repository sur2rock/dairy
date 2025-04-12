from django.db import models
from django.utils import timezone
from configuration.models import GlobalSettings


class Breed(models.Model):
    """Buffalo breed information"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Buffalo(models.Model):
    """Main buffalo model for tracking each animal"""
    # Status choices
    STATUS_CHOICES = [
        ('CALF', 'Calf'),
        ('HEIFER', 'Heifer'),
        ('MILKING', 'Active-Milking'),
        ('DRY', 'Active-Dry'),
        ('PREGNANT', 'Active-Pregnant'),
        ('SOLD', 'Sold'),
        ('DECEASED', 'Deceased'),
    ]

    # Gender choices
    GENDER_CHOICES = [
        ('FEMALE', 'Female'),
        ('MALE', 'Male'),
    ]

    # Basic identification
    buffalo_id = models.CharField(max_length=20, unique=True, help_text="Unique tag/ID number")
    name = models.CharField(max_length=100, blank=True, null=True)
    breed = models.ForeignKey(Breed, on_delete=models.PROTECT)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)

    # Acquisition information
    purchase_date = models.DateField(blank=True, null=True, help_text="Leave blank if born on farm")
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    # Status and location
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='CALF')
    current_location = models.CharField(max_length=100, default="Main Facility")

    # Family relationships
    dam = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='dam_children')
    sire = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='sire_children')

    # Reproductive information
    date_last_calved = models.DateField(blank=True, null=True)
    date_due = models.DateField(blank=True, null=True, help_text="Expected calving date if pregnant")
    expected_dry_off_date = models.DateField(blank=True, null=True)
    lactation_number = models.PositiveIntegerField(default=0)

    # Financial tracking
    cumulative_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # Additional info
    notes = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='buffalo_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Custom fields (stored as JSON)
    custom_data = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.name:
            return f"{self.buffalo_id} - {self.name}"
        return self.buffalo_id

    @property
    def age(self):
        """Calculate age in years and months"""
        if not self.date_of_birth:
            return None

        today = timezone.now().date()
        years = today.year - self.date_of_birth.year
        months = today.month - self.date_of_birth.month

        if today.day < self.date_of_birth.day:
            months -= 1

        if months < 0:
            years -= 1
            months += 12

        return f"{years} years, {months} months"

    def calculate_expected_dry_off_date(self):
        """Calculate expected dry off date based on last calving date"""
        if self.date_last_calved and self.status == 'MILKING':
            settings = GlobalSettings.objects.first()
            if settings:
                return self.date_last_calved + timezone.timedelta(days=settings.default_lactation_period_days)
        return None

    def calculate_due_date(self, breeding_date):
        """Calculate expected calving date based on breeding date"""
        settings = GlobalSettings.objects.first()
        if settings:
            return breeding_date + timezone.timedelta(days=settings.default_pregnancy_duration_days)
        # Default to 280 days if settings not available
        return breeding_date + timezone.timedelta(days=280)

    def save(self, *args, **kwargs):
        # Calculate expected dry off date if needed
        if self.date_last_calved and self.status == 'MILKING' and not self.expected_dry_off_date:
            self.expected_dry_off_date = self.calculate_expected_dry_off_date()

        # Add purchase price to cumulative cost if this is a new purchase
        if self.purchase_price and self.purchase_date and self._state.adding:
            self.cumulative_cost = self.purchase_price

        super().save(*args, **kwargs)


class LifecycleEvent(models.Model):
    """Records lifecycle events for buffalo"""
    EVENT_TYPES = [
        ('BIRTH', 'Birth'),
        ('PURCHASE', 'Purchase'),
        ('CALVING', 'Calving'),
        ('WEANING', 'Weaning'),
        ('DRYOFF', 'Dry Off'),
        ('BRED', 'Bred'),
        ('PREG_CONFIRMED', 'Pregnancy Confirmed'),
        ('SALE', 'Sale'),
        ('DEATH', 'Death'),
    ]

    buffalo = models.ForeignKey(Buffalo, on_delete=models.CASCADE, related_name='lifecycle_events')
    event_type = models.CharField(max_length=15, choices=EVENT_TYPES)
    event_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    related_calf = models.ForeignKey(Buffalo, on_delete=models.SET_NULL, blank=True, null=True,
                                     related_name='birth_event')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.buffalo} - {self.get_event_type_display()} on {self.event_date}"

    def save(self, *args, **kwargs):
        # Auto-update Buffalo status based on event type
        if self._state.adding:  # Only on creation of new event
            buffalo = self.buffalo
            if self.event_type == 'CALVING':
                buffalo.status = 'MILKING'
                buffalo.date_last_calved = self.event_date
                buffalo.lactation_number += 1
                buffalo.date_due = None
            elif self.event_type == 'DRYOFF':
                buffalo.status = 'DRY'
            elif self.event_type == 'BRED':
                # If currently Dry or Heifer, mark as Pregnant
                if buffalo.status in ['DRY', 'HEIFER']:
                    buffalo.status = 'PREGNANT'
                # Calculate and set due date
                buffalo.date_due = buffalo.calculate_due_date(self.event_date)
            elif self.event_type == 'PREG_CONFIRMED':
                buffalo.status = 'PREGNANT'
            elif self.event_type == 'SALE':
                buffalo.status = 'SOLD'
                buffalo.is_active = False
            elif self.event_type == 'DEATH':
                buffalo.status = 'DECEASED'
                buffalo.is_active = False

            # Save the buffalo record
            buffalo.save()

        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-event_date']


class MilkProduction(models.Model):
    """Records daily milk production for each buffalo"""
    TIME_CHOICES = [
        ('AM', 'Morning'),
        ('PM', 'Evening'),
    ]

    buffalo = models.ForeignKey(Buffalo, on_delete=models.CASCADE, related_name='milk_records')
    date = models.DateField()
    time_of_day = models.CharField(max_length=2, choices=TIME_CHOICES)
    quantity_litres = models.DecimalField(max_digits=6, decimal_places=2)
    somatic_cell_count = models.PositiveIntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.buffalo} - {self.date} {self.get_time_of_day_display()}: {self.quantity_litres} L"

    class Meta:
        unique_together = ['buffalo', 'date', 'time_of_day']
        ordering = ['-date', '-time_of_day']