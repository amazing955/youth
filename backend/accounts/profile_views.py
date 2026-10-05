from django.utils import timezone
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog, Member, Notification, SupportIssue
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


class SupportMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = str(request.data.get('message', '')).strip()
        if not message:
            return Response({'detail': 'Write a message before sending.'}, status=400)
        if len(message) > 2000:
            return Response({'detail': 'Message must be 2000 characters or fewer.'}, status=400)
        AuditLog.objects.create(
            user=request.user,
            action='support_message_received',
            object_type='SupportMessage',
            object_id=str(request.user.id),
            description=f'Support message from {request.user.get_full_name() or request.user.username}: {message}',
        )
        return Response({'message': 'Your message has been sent to the SACCO admin.'}, status=201)


class AdminSupportReplyView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        user_id = request.data.get('user_id')
        message = str(request.data.get('message', '')).strip()
        if not message:
            return Response({'detail': 'Write a reply before sending.'}, status=400)
        if len(message) > 2000:
            return Response({'detail': 'Reply must be 2000 characters or fewer.'}, status=400)
        member = Member.objects.filter(user_id=user_id).first()
        if not member:
            return Response({'detail': 'Member not found.'}, status=404)
        Notification.objects.create(member=member, title='Reply from SACCO admin', message=message, kind='Support')
        AuditLog.objects.create(user=request.user, action='support_reply_sent', object_type='Member', object_id=str(member.id), description=f'Admin replied to {member.full_name}: {message}')
        return Response({'message': 'Reply sent to the member.'}, status=201)


class AdminSupportIssueView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response([{
            'id': issue.id,
            'member_id': issue.member.user_id,
            'member_name': issue.member.full_name,
            'title': issue.title,
            'description': issue.description,
            'status': issue.status,
            'report': issue.report,
            'created_at': issue.created_at,
            'resolved_at': issue.resolved_at,
        } for issue in SupportIssue.objects.select_related('member__user').all()])

    def post(self, request):
        member = Member.objects.filter(user_id=request.data.get('user_id')).first()
        description = str(request.data.get('description', '')).strip()
        if not member or not description:
            return Response({'detail': 'A member and issue description are required.'}, status=400)
        issue = SupportIssue.objects.create(member=member, description=description)
        AuditLog.objects.create(user=request.user, action='support_issue_created', object_type='SupportIssue', object_id=str(issue.id), description=f'Admin created a support issue for {member.full_name}.')
        return Response({'id': issue.id, 'status': issue.status}, status=201)


class AdminSupportIssueResolveView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, issue_id):
        report = str(request.data.get('report', '')).strip()
        if not report:
            return Response({'detail': 'A resolution report is required.'}, status=400)
        issue = SupportIssue.objects.filter(pk=issue_id).first()
        if not issue:
            return Response({'detail': 'Issue not found.'}, status=404)
        issue.status = SupportIssue.Status.RESOLVED
        issue.report = report
        issue.resolved_by = request.user
        issue.resolved_at = timezone.now()
        issue.save(update_fields=['status', 'report', 'resolved_by', 'resolved_at'])
        AuditLog.objects.create(user=request.user, action='support_issue_resolved', object_type='SupportIssue', object_id=str(issue.id), description=f'Admin resolved support issue for {issue.member.full_name}: {report}')
        return Response({'id': issue.id, 'status': issue.status, 'report': issue.report, 'resolved_at': issue.resolved_at}, status=200)
