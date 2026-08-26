from rest_framework import serializers
from .models import Notice


class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ['id', 'title', 'message', 'kind', 'member', 'created_by', 'created_at', 'is_read']
        read_only_fields = ['id', 'member', 'created_by', 'created_at']
