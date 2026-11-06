"""Stores a seed distribution record: who received seeds, and what they received."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import SeedInventory


class Info(models.Model):
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(150)])
    address = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, blank=True)
    seed = models.ForeignKey(
        SeedInventory,
        related_name='distributions',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    quantity_issued = models.PositiveIntegerField(default=0)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='infos',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tblinfo'
        ordering = ['name']
        verbose_name = "Seed Distribution"
        verbose_name_plural = "Seed Distributions"

    def __str__(self):
        return self.name
