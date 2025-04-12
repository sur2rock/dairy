from rest_framework import serializers
from .models import ExpenseCategory, IncomeCategory, ExpenseRecord, IncomeRecord, Profitability
from herd.serializers import BuffaloListSerializer


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = '__all__'


class IncomeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomeCategory
        fields = '__all__'


class ExpenseRecordListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing expense records"""
    category_name = serializers.ReadOnlyField(source='category.name')

    class Meta:
        model = ExpenseRecord
        fields = ['id', 'date', 'category', 'category_name', 'description', 'amount', 'supplier_vendor']


class ExpenseRecordSerializer(serializers.ModelSerializer):
    """Full serializer for expense record details"""
    category_name = serializers.ReadOnlyField(source='category.name')
    related_buffalo_info = BuffaloListSerializer(source='related_buffalo', read_only=True)

    class Meta:
        model = ExpenseRecord
        fields = '__all__'


class IncomeRecordListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing income records"""
    category_name = serializers.ReadOnlyField(source='category.name')

    class Meta:
        model = IncomeRecord
        fields = ['id', 'date', 'category', 'category_name', 'description', 'total_amount', 'customer']


class IncomeRecordSerializer(serializers.ModelSerializer):
    """Full serializer for income record details"""
    category_name = serializers.ReadOnlyField(source='category.name')
    related_buffalo_info = BuffaloListSerializer(source='related_buffalo', read_only=True)

    class Meta:
        model = IncomeRecord
        fields = '__all__'


class ProfitabilitySerializer(serializers.ModelSerializer):
    """Serializer for profitability records"""
    month_name = serializers.SerializerMethodField()

    class Meta:
        model = Profitability
        fields = '__all__'

    def get_month_name(self, obj):
        """Return the month name for display"""
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        return month_names[obj.month - 1]