from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CancelLoanView, LoanViewSet
from .loan_views import LoanTermsView

router = DefaultRouter()
router.register('loans', LoanViewSet, basename='loan')
urlpatterns = [path('loans/terms/', LoanTermsView.as_view(), name='loan-terms'), path('loans/<int:loan_id>/cancel/', CancelLoanView.as_view(), name='loan-cancel'), path('', include(router.urls))]
