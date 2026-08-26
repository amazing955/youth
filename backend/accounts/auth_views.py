from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth_serializers import LoginSerializer, RegisterSerializer

User = get_user_model()


def user_payload(user):
    return {'id': user.id, 'username': user.username, 'full_name': user.get_full_name() or user.username, 'role': 'admin' if user.is_staff else 'member'}


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token, _ = Token.objects.get_or_create(user=serializer.validated_data['user'])
        return Response({'message': 'Login successful', 'token': token.key, 'user': user_payload(serializer.validated_data['user'])})


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({'message': 'Registration successful', 'user': user_payload(user)}, status=status.HTTP_201_CREATED)
