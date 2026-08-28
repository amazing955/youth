from django.contrib import admin
from .models import AuditLog, Member, Notice, SACCOSettings


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'phone_number', 'email', 'is_active', 'date_joined']
    search_fields = ['full_name', 'phone_number', 'email']
    list_filter = ['is_active', 'gender', 'date_joined']
    ordering = ['-date_joined']


@admin.register(SACCOSettings)
class SACCOSettingsAdmin(admin.ModelAdmin):
    list_display = ['sacco_name', 'loan_interest_rate', 'mtn_number', 'airtel_number', 'whatsapp_group_link', 'updated_by', 'updated_at']
    search_fields = ['sacco_name', 'mtn_number', 'airtel_number']
    ordering = ['-updated_at']

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'object_type', 'user', 'created_at']
    search_fields = ['action', 'object_type', 'description']
    list_filter = ['action', 'object_type', 'created_at']
    ordering = ['-created_at']


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ['title', 'kind', 'member', 'created_by', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'member__full_name']
    list_filter = ['kind', 'is_read', 'created_at']
    ordering = ['-created_at']
