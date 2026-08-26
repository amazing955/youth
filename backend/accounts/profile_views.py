from django.utils import timezone
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog
from .profile_serializers import ChangePasswordSerializer, ProfileSerializer


class ProfileView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        return Response(ProfileSerializer(request.user.member_profile, context={'request': request}).data)

    def patch(self, request):
        member = request.user.member_profile
        serializer = ProfileSerializer(member, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        return Response(ProfileSerializer(member, context={'request': request}).data)


class ProfilePictureView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        member = request.user.member_profile
        serializer = ProfileSerializer(member, data={'profile_image': request.FILES.get('profile_picture')}, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        return Response(ProfileSerializer(member, context={'request': request}).data)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        AuditLog.objects.create(user=request.user, action='password_changed', object_type='User', object_id=str(request.user.id), description='Member changed their password.')
        return Response({'message': 'Password changed successfully.'})
