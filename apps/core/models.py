from django.db import models

LOW_STOCK_THRESHOLD = 10


class SeedInventory(models.Model):
    CATEGORY_CHOICES = [
        ("vegetable", "Vegetable"),
        ("fruit", "Fruit"),
        ("herb", "Herb"),
        ("flower", "Flower"),
        ("grain", "Grain"),
        ("other", "Other"),
    ]

    UNIT_CHOICES = [
        ("packets", "Packets"),
        ("grams", "Grams"),
        ("kilograms", "Kilograms"),
        ("pieces", "Pieces"),
    ]

    seed_name = models.CharField(max_length=150)
    variety = models.CharField(max_length=150, blank=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="other",
    )
    image = models.ImageField(
        upload_to="seeds/",
        null=True,
        blank=True,
        help_text="Upload seed or packet image for visual identification",
    )
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default="packets",
    )
    storage_location = models.CharField(max_length=150, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["seed_name"]
        verbose_name = "Seed Inventory Item"
        verbose_name_plural = "Seed Inventory Items"

    def __str__(self):
        return f"{self.seed_name} - {self.variety}" if self.variety else self.seed_name

    @property
    def is_low_stock(self):
        return 0 < self.quantity <= LOW_STOCK_THRESHOLD

    @property
    def stock_status(self):
        if self.quantity == 0:
            return "Out of Stock"
        if self.quantity <= LOW_STOCK_THRESHOLD:
            return "Low Stock"
        return "Available"
