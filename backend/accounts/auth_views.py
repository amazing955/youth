from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth_serializers import LoginSerializer, RegisterSerializer
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
        token, _ = Token.objects.get_or_create(user=serializer.validated_data['user'])
        return Response({'message': 'Login successful', 'token': token.key, 'user': user_payload(serializer.validated_data['user'])})


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
        send_mail('Reset your Youth Saving password', f'Use this link to create a new password for your Youth Saving account:\n\n{reset_url}\n\nThis link can only be used once.', settings.DEFAULT_FROM_EMAIL, [member.user.email], fail_silently=True)
        return Response({'message': f'Password reset link sent to {member.user.email}.', 'reset_url': reset_url})
