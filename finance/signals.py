from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

from .models import ExpenseRecord
from herd.models import Buffalo


@receiver(post_save, sender=ExpenseRecord)
def update_buffalo_cumulative_cost(sender, instance, created, **kwargs):
    """Update cumulative cost of buffalo when a related expense is saved"""
    if instance.related_buffalo:
        buffalo = instance.related_buffalo

        # Only add the expense to cumulative cost if it's a new record
        if created:
            buffalo.cumulative_cost += Decimal(instance.amount)
            buffalo.save(update_fields=['cumulative_cost'])