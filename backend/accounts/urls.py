from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import DashboardView, MemberViewSet
from .auth_views import AdminPasswordResetView, LoginView, RegisterView, ResetPasswordView
from .admin_views import AdminAuditView, AdminDashboardView, AdminLoanActionView, AdminMemberDetailView, AdminMembersView, PaymentConfigView
from .profile_views import ChangePasswordView, ProfilePictureView, ProfileView
from .notice_views import AdminLoanRemindersView, AdminMemberBlockView, AdminNoticeView, NoticeView, NotificationView

router = DefaultRouter()
router.register('members', MemberViewSet, basename='member')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/me/', DashboardView.as_view(), name='dashboard-me'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='auth-reset-password'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('profile/me/', ProfileView.as_view(), name='profile-me'),
    path('profile/me/profile-picture/', ProfilePictureView.as_view(), name='profile-picture'),
    path('notices/', NoticeView.as_view(), name='notices'),
    path('notifications/', NotificationView.as_view(), name='notifications'),
    path('notifications/<int:notification_id>/read/', NotificationView.as_view(), name='notification-read'),
    path('payment-config/', PaymentConfigView.as_view(), name='payment-config'),
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/members/', AdminMembersView.as_view(), name='admin-members'),
    path('admin/members/<uuid:member_id>/', AdminMemberDetailView.as_view(), name='admin-member-detail'),
    path('admin/loans/<int:loan_id>/action/', AdminLoanActionView.as_view(), name='admin-loan-action'),
    path('admin/audit/', AdminAuditView.as_view(), name='admin-audit'),
    path('admin/notices/', AdminNoticeView.as_view(), name='admin-notices'),
    path('admin/loan-notices/generate/', AdminLoanRemindersView.as_view(), name='admin-loan-notices'),
    path('admin/members/<uuid:member_id>/block/', AdminMemberBlockView.as_view(), name='admin-member-block'),
    path('admin/members/<uuid:member_id>/password-reset/', AdminPasswordResetView.as_view(), name='admin-password-reset'),
]
