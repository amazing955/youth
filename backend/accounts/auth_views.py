import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth_serializers import LoginSerializer, RegisterSerializer
from .models import AdminLoginOTP
from .throttles import LoginRateThrottle, PasswordResetRateThrottle, RegistrationRateThrottle

User = get_user_model()


def user_payload(user):
    return {'id': user.id, 'username': user.username, 'full_name': user.get_full_name() or user.username, 'role': 'admin' if user.is_staff else 'member'}


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        if user.is_staff:
            if not user.email:
                return Response({'detail': 'An email address is required for admin OTP verification.'}, status=400)
            code = f'{secrets.randbelow(1000000):06d}'
            AdminLoginOTP.objects.filter(user=user, verified_at__isnull=True).delete()
            challenge = AdminLoginOTP.objects.create(user=user, code_hash=make_password(code), expires_at=timezone.now() + timedelta(minutes=10))
            send_mail('Your Coins and Dreams admin login code', f'Your one-time admin login code is {code}. It expires in 10 minutes.', settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            return Response({'otp_required': True, 'challenge_id': challenge.id, 'email': user.email})
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'message': 'Login successful', 'token': token.key, 'user': user_payload(user)})


class AdminOTPVerifyView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        try:
            challenge = AdminLoginOTP.objects.select_related('user').get(pk=request.data.get('challenge_id'))
        except (AdminLoginOTP.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'This admin OTP challenge is invalid.'}, status=400)
        if not challenge.is_valid():
            return Response({'detail': 'This OTP has expired or too many attempts were made.'}, status=400)
        if not check_password(str(request.data.get('code', '')), challenge.code_hash):
            challenge.attempts += 1
            challenge.save(update_fields=['attempts'])
            return Response({'detail': 'Invalid admin OTP.'}, status=400)
        challenge.verified_at = timezone.now()
        challenge.save(update_fields=['verified_at'])
        token, _ = Token.objects.get_or_create(user=challenge.user)
        return Response({'message': 'Login successful', 'token': token.key, 'user': user_payload(challenge.user)})


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [RegistrationRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({'message': 'Registration successful', 'user': user_payload(user)}, status=status.HTTP_201_CREATED)


class ResetPasswordView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        try:
            user_id = urlsafe_base64_decode(request.data.get('uid', '')).decode()
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'detail': 'This password reset link is invalid or expired.'}, status=400)
        if not default_token_generator.check_token(user, request.data.get('token', '')):
            return Response({'detail': 'This password reset link is invalid or expired.'}, status=400)
        try:
            validate_password(request.data.get('password', ''), user)
        except Exception as error:
            return Response({'detail': error.messages}, status=400)
        user.set_password(request.data['password'])
        user.save(update_fields=['password'])
        return Response({'message': 'Password reset successfully.'})


class AdminPasswordResetView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, member_id):
        from .models import Member
        try:
            member = Member.objects.select_related('user').get(pk=member_id)
        except Member.DoesNotExist:
            return Response({'detail': 'Member not found.'}, status=404)
        if not member.user or not member.user.email:
            return Response({'detail': 'This member does not have an email address.'}, status=400)
        uid = urlsafe_base64_encode(str(member.user.pk).encode())
        token = default_token_generator.make_token(member.user)
        reset_url = f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}'
        send_mail('Reset your Coins and Dreams password', f'Use this link to create a new password for your Coins and Dreams account:\n\n{reset_url}\n\nThis link can only be used once.', settings.DEFAULT_FROM_EMAIL, [member.user.email], fail_silently=True)
        return Response({'message': f'Password reset link sent to {member.user.email}.', 'reset_url': reset_url})
