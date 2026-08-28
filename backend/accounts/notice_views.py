from django.db.models import Q
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from loans.models import Loan
from .models import AuditLog, Member, Notice, Notification, SACCOSettings
from .notice_serializers import NoticeSerializer
from .notification_serializers import NotificationSerializer
from .notification_utils import notify_member, notify_members


class NoticeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notices = Notice.objects.filter(Q(member__user=request.user) | Q(member__isnull=True))
        return Response(NoticeSerializer(notices, many=True).data)


class NotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(member__user=request.user)
        return Response({
            'notifications': NotificationSerializer(notifications, many=True).data,
            'unread_count': notifications.filter(is_read=False).count(),
        })

    def patch(self, request, notification_id):
        notification = Notification.objects.filter(id=notification_id, member__user=request.user).first()
        if not notification:
            return Response({'detail': 'Notification not found.'}, status=404)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(NotificationSerializer(notification).data)


class AdminNoticeView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(NoticeSerializer(Notice.objects.all(), many=True).data)

    def post(self, request):
        serializer = NoticeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notice = serializer.save(created_by=request.user)
        notify_members(notice.title, notice.message, notice.kind)
        AuditLog.objects.create(user=request.user, action='notice_created', object_type='Notice', object_id=str(notice.id), description=f'Admin published notice: {notice.title}.')
        return Response(NoticeSerializer(notice).data, status=201)


class AdminLoanRemindersView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        kind = request.data.get('kind', Notice.Kind.REMINDER)
        if kind not in [Notice.Kind.REMINDER, Notice.Kind.DEMAND]:
            return Response({'detail': 'Kind must be Reminder or Demand.'}, status=400)
        created = []
        sacco_name = SACCOSettings.current().sacco_name
        for loan in Loan.objects.filter(outstanding_balance__gt=0, status__in=[Loan.Status.ACTIVE, Loan.Status.APPROVED]).select_related('member'):
            title = 'Loan demand note' if kind == Notice.Kind.DEMAND else 'Loan repayment reminder'
            message = f'Your outstanding loan balance is UGX {loan.outstanding_balance:,.0f}. Please make a repayment or contact {sacco_name}.'
            notice = Notice.objects.create(title=title, message=message, kind=kind, member=loan.member, created_by=request.user)
            notify_member(loan.member, title, message, kind)
            created.append(notice)
        AuditLog.objects.create(user=request.user, action=f'{kind.lower()}s_generated', object_type='Loan', description=f'Generated {len(created)} {kind.lower()} notices for outstanding loans.')
        return Response({'created': len(created), 'notices': NoticeSerializer(created, many=True).data}, status=201)


class AdminMemberBlockView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, member_id):
        try:
            member = Member.objects.select_related('user').get(pk=member_id)
        except Member.DoesNotExist:
            return Response({'detail': 'Member not found.'}, status=404)
        blocked = bool(request.data.get('blocked', True))
        member.is_active = not blocked
        member.user.is_active = not blocked
        member.save(update_fields=['is_active'])
        member.user.save(update_fields=['is_active'])
        AuditLog.objects.create(user=request.user, action='member_blocked' if blocked else 'member_unblocked', object_type='Member', object_id=str(member.id), description=f'Member {member.full_name} was {"blocked" if blocked else "unblocked"}.')
        return Response({'id': member.id, 'is_active': member.is_active})
