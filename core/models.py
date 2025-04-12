from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Extended user model"""
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_manager = models.BooleanField(default=False)
    is_accountant = models.BooleanField(default=False)
    is_veterinarian = models.BooleanField(default=False)
    is_worker = models.BooleanField(default=False)

    def __str__(self):
        return self.username