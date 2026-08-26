from rest_framework import serializers
from .models import Member


class MemberSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(source='profile_image', read_only=True)

    class Meta:
        model = Member
        fields = ['id', 'full_name', 'phone_number', 'email', 'profile_image', 'profile_picture', 'date_of_birth', 'gender', 'nin', 'address', 'next_of_kin_name', 'next_of_kin_phone', 'date_joined', 'is_active']
