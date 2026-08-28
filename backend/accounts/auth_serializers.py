from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Member

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if not user or not user.is_active:
            raise serializers.ValidationError('Invalid username or password.')
        attrs['user'] = user
        return attrs


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=30)
    date_of_birth = serializers.DateField()
    gender = serializers.ChoiceField(choices=['Male', 'Female'])
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    nin = serializers.CharField(max_length=50)
    address = serializers.CharField(max_length=255)
    next_of_kin_name = serializers.CharField(max_length=150)
    next_of_kin_phone = serializers.CharField(max_length=30)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('That username is already in use.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('That email is already in use.')
        return value

    def validate_phone_number(self, value):
        if not value.replace('+', '').replace(' ', '').replace('-', '').isdigit():
            raise serializers.ValidationError('Enter a valid phone number.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        if len(attrs['password']) < 8 or not any(character.isalpha() for character in attrs['password']) or not any(character.isdigit() for character in attrs['password']):
            raise serializers.ValidationError({'password': 'Use at least 8 characters with a letter and number.'})
        validate_password(attrs['password'])
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User.objects.create_user(
            username=validated_data.pop('username'),
            email=validated_data.pop('email'),
            first_name=validated_data.pop('first_name'),
            last_name=validated_data.pop('last_name'),
            password=password,
        )
        Member.objects.create(user=user, full_name=user.get_full_name(), email=user.email, is_active=False, **validated_data)
        return user
