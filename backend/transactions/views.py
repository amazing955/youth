from rest_framework import viewsets
from .models import Transaction
from .serializers import TransactionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = Transaction.objects.select_related('member').all()
        return queryset if self.request.user.is_staff else queryset.filter(member__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(member=self.request.user.member_profile)
