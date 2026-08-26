from django.contrib import admin
from .models import Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['member', 'loan_amount', 'amount_paid', 'outstanding_balance', 'status', 'approved_by', 'approved_at', 'created_at']
    search_fields = ['member__full_name']
    list_filter = ['status', 'created_at']
    ordering = ['-created_at']
