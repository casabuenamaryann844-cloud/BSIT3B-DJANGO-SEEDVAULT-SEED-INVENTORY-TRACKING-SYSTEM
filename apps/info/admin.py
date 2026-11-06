from django.contrib import admin

from .models import Info


@admin.register(Info)
class InfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'address', 'email', 'seed', 'quantity_issued')
    search_fields = ('name', 'address', 'email')
