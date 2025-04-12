from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

from finance.models import ExpenseRecord


class FodderType(models.Model):
    """Types of feed/fodder used on the farm"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=20, help_text="e.g., kg, bags, bales")
    category = models.CharField(max_length=20, choices=[
        ('GREEN', 'Green Fodder'),
        ('DRY', 'Dry Fodder'),
        ('CONCENTRATE', 'Concentrate'),
        ('SUPPLEMENT', 'Supplement'),
        ('OTHER', 'Other')
    ])
    current_cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nutrient_info = models.TextField(blank=True, null=True, help_text="Optional information about nutritional content")
    is_produced_in_house = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.unit})"


class FeedInventory(models.Model):
    """Tracks current inventory levels for each feed type"""
    fodder_type = models.OneToOneField(FodderType, on_delete=models.CASCADE, related_name='inventory')
    quantity_on_hand = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.fodder_type}: {self.quantity_on_hand} {self.fodder_type.unit}"

    class Meta:
        verbose_name_plural = "Feed Inventories"


class FeedPurchase(models.Model):
    """Records of feed purchases"""
    fodder_type = models.ForeignKey(FodderType, on_delete=models.PROTECT, related_name='purchases')
    date = models.DateField()
    supplier = models.CharField(max_length=100, blank=True, null=True)
    quantity_purchased = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    related_expense = models.OneToOneField(ExpenseRecord, on_delete=models.SET_NULL, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.date} - {self.fodder_type}: {self.quantity_purchased} {self.fodder_type.unit}"

    def save(self, *args, **kwargs):
        # Calculate total_cost if not set
        if not self.total_cost:
            self.total_cost = self.quantity_purchased * self.cost_per_unit

        # First time saving (creating a new purchase)
        if self._state.adding:
            # Create corresponding expense record
            from finance.models import ExpenseCategory
            feed_category, _ = ExpenseCategory.objects.get_or_create(
                name='Feed',
                defaults={
                    'description': 'Expenses related to animal feed and fodder',
                    'is_direct_cost': True
                }
            )

            expense = ExpenseRecord.objects.create(
                date=self.date,
                category=feed_category,
                description=f"Purchase of {self.quantity_purchased} {self.fodder_type.unit} of {self.fodder_type.name}",
                amount=self.total_cost,
                supplier_vendor=self.supplier,
                notes=self.notes,
                related_module='FeedPurchase'
            )

            self.related_expense = expense

        super().save(*args, **kwargs)


class FeedConsumption(models.Model):
    """Records of feed consumed"""
    CONSUMPTION_TYPES = [
        ('HERD', 'Whole Herd'),
        ('GROUP', 'Specific Group'),
        ('INDIVIDUAL', 'Individual Buffalo'),
    ]

    fodder_type = models.ForeignKey(FodderType, on_delete=models.PROTECT, related_name='consumption_records')
    date = models.DateField()
    quantity_consumed = models.DecimalField(max_digits=10, decimal_places=2)
    consumed_by = models.CharField(max_length=20, choices=CONSUMPTION_TYPES, default='HERD')
    group_name = models.CharField(max_length=100, blank=True, null=True, help_text="If consumed by a specific group")
    buffalo = models.ForeignKey('herd.Buffalo', on_delete=models.SET_NULL, blank=True, null=True,
                                help_text="If consumed by an individual buffalo")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.consumed_by == 'INDIVIDUAL' and self.buffalo:
            consumer = str(self.buffalo)
        elif self.consumed_by == 'GROUP' and self.group_name:
            consumer = self.group_name
        else:
            consumer = "Whole Herd"

        return f"{self.date} - {self.fodder_type}: {self.quantity_consumed} {self.fodder_type.unit} by {consumer}"


class InHouseFeedProduction(models.Model):
    """Records for feed produced on the farm"""
    fodder_type = models.ForeignKey(FodderType, on_delete=models.PROTECT, related_name='production_records')
    date = models.DateField()
    quantity_produced = models.DecimalField(max_digits=10, decimal_places=2)

    # Associated costs
    seed_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fertilizer_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    machinery_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_costs = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Calculated fields
    total_production_cost = models.DecimalField(max_digits=12, decimal_places=2)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)

    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.date} - Produced {self.quantity_produced} {self.fodder_type.unit} of {self.fodder_type.name}"

    def save(self, *args, **kwargs):
        # Calculate total production cost
        self.total_production_cost = (
                self.seed_cost +
                self.fertilizer_cost +
                self.labor_cost +
                self.machinery_cost +
                self.other_costs
        )

        # Calculate cost per unit
        if self.quantity_produced > 0:
            self.cost_per_unit = self.total_production_cost / self.quantity_produced
        else:
            self.cost_per_unit = 0

        super().save(*args, **kwargs)