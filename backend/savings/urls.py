from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import SavingsViewSet
from .payment_views import AdminPaymentActionView, PaymentStartView, PaymentViewSet, ReconcilePaymentView, SaccoSettingsView

router = DefaultRouter()
router.register('savings', SavingsViewSet, basename='savings')
router.register('payments', PaymentViewSet, basename='payment')
urlpatterns = [
	path('payments/start/', PaymentStartView.as_view(), name='payment-start'),
	path('payments/reconcile/', ReconcilePaymentView.as_view(), name='payment-reconcile'),
	path('admin/payments/<int:payment_id>/action/', AdminPaymentActionView.as_view(), name='admin-payment-action'),
	path('admin/sacco-settings/', SaccoSettingsView.as_view(), name='sacco-settings'),
	path('', include(router.urls)),
]
