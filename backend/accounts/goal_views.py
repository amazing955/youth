from decimal import Decimal, InvalidOperation

from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from savings.models import Savings
from .models import FinancialGoal


def goal_data(goal):
    return {'id': goal.id, 'name': goal.name, 'amount': goal.amount, 'achieved_at': goal.achieved_at, 'created_at': goal.created_at}


class GoalView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([goal_data(goal) for goal in FinancialGoal.objects.filter(member=request.user.member_profile)])

    def post(self, request):
        name = str(request.data.get('name', '')).strip()
        try:
            amount = Decimal(str(request.data.get('amount')))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'detail': 'Enter a valid goal amount.'}, status=400)
        if not name or not amount.is_finite() or amount <= 0:
            return Response({'detail': 'Enter a goal name and a positive amount.'}, status=400)
        goal = FinancialGoal.objects.create(member=request.user.member_profile, name=name, amount=amount)
        return Response(goal_data(goal), status=201)


class GoalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, goal_id):
        goal = FinancialGoal.objects.filter(pk=goal_id, member=request.user.member_profile).first()
        if not goal:
            return Response({'detail': 'Goal not found.'}, status=404)
        name = str(request.data.get('name', goal.name)).strip()
        try:
            amount = Decimal(str(request.data.get('amount', goal.amount)))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'detail': 'Enter a valid goal amount.'}, status=400)
        if not name or not amount.is_finite() or amount <= 0:
            return Response({'detail': 'Enter a goal name and a positive amount.'}, status=400)
        goal.name = name
        goal.amount = amount
        goal.achieved_at = None
        goal.save(update_fields=['name', 'amount', 'achieved_at', 'updated_at'])
        return Response(goal_data(goal))