
from django import forms
from .models import SeedInventory


class SeedInventoryForm(forms.ModelForm):
    class Meta:
        model = SeedInventory
        fields = [
            "seed_name",
            "variety",
            "category",
            "image",
            "quantity",
            "unit",
            "storage_location",
            "expiration_date",
            "notes",
        ]
        widgets = {
            "seed_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter seed name",
            }),
            "variety": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter seed variety",
            }),
            "category": forms.Select(attrs={
                "class": "form-select",
            }),
            "image": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/*",
            }),
            "quantity": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "placeholder": "Enter quantity",
            }),
            "unit": forms.Select(attrs={
                "class": "form-select",
            }),
            "storage_location": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter storage location",
            }),
            "expiration_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Add notes (optional)",
            }),
        }
