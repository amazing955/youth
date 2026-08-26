from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'member', 'amount', 'payment_method', 'status', 'created_at']
    search_fields = ['member__full_name', 'reference', 'description']
    list_filter = ['transaction_type', 'status', 'payment_method', 'created_at']
    ordering = ['-created_at']
