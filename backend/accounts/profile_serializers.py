from django.contrib.auth import password_validation
from django.core.files.images import get_image_dimensions
from rest_framework import serializers
from PIL import Image

from .models import Member


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    profile_picture = serializers.ImageField(source='profile_image', read_only=True)
    profile_image = serializers.ImageField(write_only=True, required=False)
    date_joined = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Member
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email', 'phone_number', 'date_of_birth', 'gender', 'address', 'nin', 'profile_image', 'profile_picture', 'date_joined']
        read_only_fields = ['id', 'username', 'full_name', 'nin', 'profile_picture', 'date_joined']

    def validate_profile_image(self, image):
        if image.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Profile pictures must be 5 MB or smaller.')
        if getattr(image, 'content_type', '') not in {'image/jpeg', 'image/png', 'image/webp'}:
            raise serializers.ValidationError('Upload a valid JPG, PNG, or WEBP image.')
        try:
            width, height = get_image_dimensions(image)
            image.seek(0)
            with Image.open(image) as uploaded_image:
                uploaded_image.verify()
            image.seek(0)
        except Exception as error:
            raise serializers.ValidationError('Upload a valid JPG, PNG, or WEBP image.') from error
        if not width or not height or width > 4096 or height > 4096:
            raise serializers.ValidationError('Upload a valid image file.')
        return image

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user
        for field in ['first_name', 'last_name']:
            if field in user_data:
                setattr(user, field, user_data[field])
        if 'email' in validated_data:
            user.email = validated_data['email']
        user.save()
        for field, value in validated_data.items():
            if field != 'email':
                setattr(instance, field, value)
        instance.full_name = user.get_full_name()
        instance.email = user.email
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        password_validation.validate_password(attrs['new_password'], user)
        return attrs
