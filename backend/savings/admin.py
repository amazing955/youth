from django.contrib import admin
from .models import Payment, Savings


@admin.register(Savings)
class SavingsAdmin(admin.ModelAdmin):
    list_display = ['member', 'amount', 'payment_method', 'transaction_reference', 'created_at']
    search_fields = ['member__full_name', 'transaction_reference']
    list_filter = ['payment_method', 'created_at']
    ordering = ['-created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['internal_reference', 'member', 'provider', 'amount', 'status', 'created_at', 'verified_at']
    search_fields = ['internal_reference', 'transaction_id', 'member__full_name']
    list_filter = ['provider', 'status', 'source', 'created_at']
    ordering = ['-created_at']
