from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
import csv
import io
import json
import datetime

from .models import ExpenseCategory, IncomeCategory, ExpenseRecord, IncomeRecord, Profitability
from .forms import ExpenseCategoryForm, IncomeCategoryForm, ExpenseRecordForm, IncomeRecordForm, MilkIncomeGeneratorForm
from .serializers import ExpenseCategorySerializer, IncomeCategorySerializer, ExpenseRecordSerializer, \
    IncomeRecordSerializer, ProfitabilitySerializer
from herd.models import MilkProduction
from configuration.models import GlobalSettings


# Expense Category Views
@login_required
def expense_category_list(request):
    """Display all expense categories"""
    categories = ExpenseCategory.objects.all()

    # Count expenses per category
    for category in categories:
        category.expense_count = ExpenseRecord.objects.filter(category=category).count()
        category.expense_total = ExpenseRecord.objects.filter(category=category).aggregate(total=Sum('amount'))[
                                     'total'] or 0

    context = {
        'title': 'Expense Categories',
        'categories': categories,
    }
    return render(request, 'dairy_erp/finance/expense_category_list.html', context)


@login_required
def expense_category_add(request):
    """Add a new expense category"""
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Expense category {category.name} has been added successfully!')
            return redirect('finance:expense_category_list')
    else:
        form = ExpenseCategoryForm()

    context = {
        'title': 'Add Expense Category',
        'form': form,
    }
    return render(request, 'dairy_erp/finance/expense_category_form.html', context)


@login_required
def expense_category_edit(request, category_id):
    """Edit an existing expense category"""
    category = get_object_or_404(ExpenseCategory, id=category_id)

    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Expense category {category.name} has been updated successfully!')
            return redirect('finance:expense_category_list')
    else:
        form = ExpenseCategoryForm(instance=category)

    context = {
        'title': 'Edit Expense Category',
        'form': form,
        'category': category,
    }
    return render(request, 'dairy_erp/finance/expense_category_form.html', context)


# Income Category Views
@login_required
def income_category_list(request):
    """Display all income categories"""
    categories = IncomeCategory.objects.all()

    # Count income records per category
    for category in categories:
        category.income_count = IncomeRecord.objects.filter(category=category).count()
        category.income_total = IncomeRecord.objects.filter(category=category).aggregate(total=Sum('total_amount'))[
                                    'total'] or 0

    context = {
        'title': 'Income Categories',
        'categories': categories,
    }
    return render(request, 'dairy_erp/finance/income_category_list.html', context)


@login_required
def income_category_add(request):
    """Add a new income category"""
    if request.method == 'POST':
        form = IncomeCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Income category {category.name} has been added successfully!')
            return redirect('finance:income_category_list')
    else:
        form = IncomeCategoryForm()

    context = {
        'title': 'Add Income Category',
        'form': form,
    }
    return render(request, 'dairy_erp/finance/income_category_form.html', context)


@login_required
def income_category_edit(request, category_id):
    """Edit an existing income category"""
    category = get_object_or_404(IncomeCategory, id=category_id)

    if request.method == 'POST':
        form = IncomeCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Income category {category.name} has been updated successfully!')
            return redirect('finance:income_category_list')
    else:
        form = IncomeCategoryForm(instance=category)

    context = {
        'title': 'Edit Income Category',
        'form': form,
        'category': category,
    }
    return render(request, 'dairy_erp/finance/income_category_form.html', context)


# Expense Record Views
@login_required
def expense_list(request):
    """Display expense records with filtering options"""
    today = timezone.now().date()
    start_date = request.GET.get('start_date', (today - datetime.timedelta(days=30)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    category_id = request.GET.get('category_id', '')

    expenses = ExpenseRecord.objects.all()

    if start_date:
        expenses = expenses.filter(date__gte=start_date)

    if end_date:
        expenses = expenses.filter(date__lte=end_date)

    if category_id:
        expenses = expenses.filter(category_id=category_id)

    # Get all expense categories for the filter dropdown
    categories = ExpenseCategory.objects.all()

    # Calculate total expenses
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0

    # Prepare data for expense breakdown chart
    expense_breakdown = expenses.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    chart_labels = [entry['category__name'] for entry in expense_breakdown]
    chart_values = [float(entry['total']) for entry in expense_breakdown]

    context = {
        'title': 'Expenses',
        'expenses': expenses,
        'categories': categories,
        'start_date': start_date,
        'end_date': end_date,
        'category_id': category_id,
        'total_expenses': total_expenses,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
    }
    return render(request, 'dairy_erp/finance/expense_list.html', context)


@login_required
def expense_add(request):
    """Add a new expense record"""
    if request.method == 'POST':
        form = ExpenseRecordForm(request.POST)
        if form.is_valid():
            expense = form.save()
            messages.success(request, f'Expense record has been added successfully!')
            return redirect('finance:expense_list')
    else:
        form = ExpenseRecordForm(initial={'date': timezone.now().date()})

    context = {
        'title': 'Add Expense',
        'form': form,
    }
    return render(request, 'dairy_erp/finance/expense_form.html', context)


@login_required
def expense_edit(request, expense_id):
    """Edit an existing expense record"""
    expense = get_object_or_404(ExpenseRecord, id=expense_id)

    if request.method == 'POST':
        form = ExpenseRecordForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, f'Expense record has been updated successfully!')
            return redirect('finance:expense_list')
    else:
        form = ExpenseRecordForm(instance=expense)

    context = {
        'title': 'Edit Expense',
        'form': form,
        'expense': expense,
    }
    return render(request, 'dairy_erp/finance/expense_form.html', context)


@login_required
def expense_delete(request, expense_id):
    """Delete an expense record"""
    expense = get_object_or_404(ExpenseRecord, id=expense_id)

    if request.method == 'POST':
        expense.delete()
        messages.success(request, f'Expense record has been deleted successfully!')
        return redirect('finance:expense_list')

    context = {
        'title': 'Delete Expense',
        'expense': expense,
    }
    return render(request, 'dairy_erp/finance/expense_delete.html', context)


@login_required
def export_expenses(request):
    """Export expense data to CSV"""
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    category_id = request.GET.get('category_id', '')

    expenses = ExpenseRecord.objects.all()

    if start_date:
        expenses = expenses.filter(date__gte=start_date)

    if end_date:
        expenses = expenses.filter(date__lte=end_date)

    if category_id:
        expenses = expenses.filter(category_id=category_id)

    # Create CSV file
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Write header row
    writer.writerow(['Date', 'Category', 'Description', 'Amount', 'Supplier/Vendor', 'Related Buffalo', 'Notes'])

    # Write data rows
    for expense in expenses:
        writer.writerow([
            expense.date,
            expense.category.name,
            expense.description,
            expense.amount,
            expense.supplier_vendor or '',
            str(expense.related_buffalo) if expense.related_buffalo else '',
            expense.notes or ''
        ])

    # Prepare response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='text/csv')
    response[
        'Content-Disposition'] = f'attachment; filename="expenses_export_{timezone.now().strftime("%Y_%m_%d")}.csv"'

    return response


# Income Record Views
@login_required
def income_list(request):
    """Display income records with filtering options"""
    today = timezone.now().date()
    start_date = request.GET.get('start_date', (today - datetime.timedelta(days=30)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    category_id = request.GET.get('category_id', '')

    income_records = IncomeRecord.objects.all()

    if start_date:
        income_records = income_records.filter(date__gte=start_date)

    if end_date:
        income_records = income_records.filter(date__lte=end_date)

    if category_id:
        income_records = income_records.filter(category_id=category_id)

    # Get all income categories for the filter dropdown
    categories = IncomeCategory.objects.all()

    # Calculate total income
    total_income = income_records.aggregate(total=Sum('total_amount'))['total'] or 0

    # Prepare data for income breakdown chart
    income_breakdown = income_records.values('category__name').annotate(
        total=Sum('total_amount')
    ).order_by('-total')

    chart_labels = [entry['category__name'] for entry in income_breakdown]
    chart_values = [float(entry['total']) for entry in income_breakdown]

    context = {
        'title': 'Income',
        'income_records': income_records,
        'categories': categories,
        'start_date': start_date,
        'end_date': end_date,
        'category_id': category_id,
        'total_income': total_income,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
    }
    return render(request, 'dairy_erp/finance/income_list.html', context)


@login_required
def income_add(request):
    """Add a new income record"""
    if request.method == 'POST':
        form = IncomeRecordForm(request.POST)
        if form.is_valid():
            income = form.save()
            messages.success(request, f'Income record has been added successfully!')
            return redirect('finance:income_list')
    else:
        form = IncomeRecordForm(initial={'date': timezone.now().date()})

    context = {
        'title': 'Add Income',
        'form': form,
    }
    return render(request, 'dairy_erp/finance/income_form.html', context)


@login_required
def income_edit(request, income_id):
    """Edit an existing income record"""
    income = get_object_or_404(IncomeRecord, id=income_id)

    if request.method == 'POST':
        form = IncomeRecordForm(request.POST, instance=income)
        if form.is_valid():
            form.save()
            messages.success(request, f'Income record has been updated successfully!')
            return redirect('finance:income_list')
    else:
        form = IncomeRecordForm(instance=income)

    context = {
        'title': 'Edit Income',
        'form': form,
        'income': income,
    }
    return render(request, 'dairy_erp/finance/income_form.html', context)


@login_required
def income_delete(request, income_id):
    """Delete an income record"""
    income = get_object_or_404(IncomeRecord, id=income_id)

    if request.method == 'POST':
        income.delete()
        messages.success(request, f'Income record has been deleted successfully!')
        return redirect('finance:income_list')

    context = {
        'title': 'Delete Income',
        'income': income,
    }
    return render(request, 'dairy_erp/finance/income_delete.html', context)


@login_required
def export_income(request):
    """Export income data to CSV"""
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    category_id = request.GET.get('category_id', '')

    income_records = IncomeRecord.objects.all()

    if start_date:
        income_records = income_records.filter(date__gte=start_date)

    if end_date:
        income_records = income_records.filter(date__lte=end_date)

    if category_id:
        income_records = income_records.filter(category_id=category_id)

    # Create CSV file
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Write header row
    writer.writerow(
        ['Date', 'Category', 'Description', 'Quantity', 'Unit Price', 'Total Amount', 'Customer', 'Related Buffalo',
         'Notes'])

    # Write data rows
    for income in income_records:
        writer.writerow([
            income.date,
            income.category.name,
            income.description,
            income.quantity or '',
            income.unit_price or '',
            income.total_amount,
            income.customer or '',
            str(income.related_buffalo) if income.related_buffalo else '',
            income.notes or ''
        ])

    # Prepare response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="income_export_{timezone.now().strftime("%Y_%m_%d")}.csv"'

    return response


@login_required
def milk_income_generator(request):
    """Auto-generate income records from milk production data"""
    if request.method == 'POST':
        form = MilkIncomeGeneratorForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            milk_price = form.cleaned_data['milk_price']
            customer = form.cleaned_data['customer']

            # Get milk production data for the date range
            milk_production = MilkProduction.objects.filter(date__gte=start_date, date__lte=end_date)

            # Group production by date
            milk_by_date = {}
            for record in milk_production:
                date_key = record.date
                if date_key not in milk_by_date:
                    milk_by_date[date_key] = 0
                milk_by_date[date_key] += record.quantity_litres

            # Create income records
            records_created = 0
            for date, quantity in milk_by_date.items():
                # Check if a record for this date already exists
                existing = IncomeRecord.objects.filter(
                    date=date,
                    category__name='Milk Sales'
                ).exists()

                if not existing:
                    # Get or create 'Milk Sales' category
                    milk_category, _ = IncomeCategory.objects.get_or_create(
                        name='Milk Sales',
                        defaults={'description': 'Income from selling milk'}
                    )

                    # Create income record
                    IncomeRecord.objects.create(
                        date=date,
                        category=milk_category,
                        description=f'Milk sales for {date.strftime("%Y-%m-%d")}',
                        quantity=quantity,
                        unit_price=milk_price,
                        total_amount=quantity * milk_price,
                        customer=customer,
                        notes='Auto-generated from milk production records'
                    )
                    records_created += 1

            messages.success(request, f'{records_created} income records have been generated!')
            return redirect('finance:income_list')
    else:
        # Set default dates (last 7 days)
        end_date = timezone.now().date()
        start_date = end_date - datetime.timedelta(days=7)

        form = MilkIncomeGeneratorForm(initial={
            'start_date': start_date,
            'end_date': end_date,
        })

    context = {
        'title': 'Generate Milk Income',
        'form': form,
    }
    return render(request, 'dairy_erp/finance/milk_income_generator.html', context)


# Profitability Views
@login_required
def profitability(request):
    """Display profitability summary and charts"""
    # Get profitability records for the last 12 months
    today = timezone.now().date()
    start_date = today.replace(day=1, month=today.month - 11 if today.month > 11 else today.month + 1,
                               year=today.year - 1 if today.month <= 11 else today.year)

    # Get all profitability records
    profitability_records = Profitability.objects.filter(
        year__gte=start_date.year,
        month__gte=start_date.month if start_date.year == today.year else 1
    ).order_by('year', 'month')

    # If no records found, calculate on-the-fly
    if not profitability_records:
        current_date = start_date
        while current_date <= today:
            year = current_date.year
            month = current_date.month

            # Get income for this month
            income = IncomeRecord.objects.filter(
                date__year=year,
                date__month=month
            ).aggregate(total=Sum('total_amount'))['total'] or 0

            # Get expenses for this month
            direct_expenses = ExpenseRecord.objects.filter(
                date__year=year,
                date__month=month,
                category__is_direct_cost=True
            ).aggregate(total=Sum('amount'))['total'] or 0

            indirect_expenses = ExpenseRecord.objects.filter(
                date__year=year,
                date__month=month,
                category__is_direct_cost=False
            ).aggregate(total=Sum('amount'))['total'] or 0

            # Calculate profits
            gross_profit = income - direct_expenses
            net_profit = gross_profit - indirect_expenses

            # Create profitability record
            Profitability.objects.create(
                year=year,
                month=month,
                total_income=income,
                direct_costs=direct_expenses,
                indirect_costs=indirect_expenses,
                gross_profit=gross_profit,
                net_profit=net_profit,
                # ROI and cash surplus calculations would be more complex
                roi_percentage=0,
                cash_surplus=0
            )

            # Move to next month
            if month == 12:
                current_date = current_date.replace(year=year + 1, month=1)
            else:
                current_date = current_date.replace(month=month + 1)

        # Reload profitability records
        profitability_records = Profitability.objects.filter(
            year__gte=start_date.year,
            month__gte=start_date.month if start_date.year == today.year else 1
        ).order_by('year', 'month')

    # Prepare data for charts
    months = []
    income_data = []
    direct_costs_data = []
    indirect_costs_data = []
    gross_profit_data = []
    net_profit_data = []

    for record in profitability_records:
        month_label = f"{record.year}-{record.month:02d}"
        months.append(month_label)
        income_data.append(float(record.total_income))
        direct_costs_data.append(float(record.direct_costs))
        indirect_costs_data.append(float(record.indirect_costs))
        gross_profit_data.append(float(record.gross_profit))
        net_profit_data.append(float(record.net_profit))

    # Calculate overall totals
    overall_income = sum(income_data)
    overall_direct_costs = sum(direct_costs_data)
    overall_indirect_costs = sum(indirect_costs_data)
    overall_gross_profit = sum(gross_profit_data)
    overall_net_profit = sum(net_profit_data)

    context = {
        'title': 'Profitability',
        'profitability_records': profitability_records,
        'months': json.dumps(months),
        'income_data': json.dumps(income_data),
        'direct_costs_data': json.dumps(direct_costs_data),
        'indirect_costs_data': json.dumps(indirect_costs_data),
        'gross_profit_data': json.dumps(gross_profit_data),
        'net_profit_data': json.dumps(net_profit_data),
        'overall_income': overall_income,
        'overall_direct_costs': overall_direct_costs,
        'overall_indirect_costs': overall_indirect_costs,
        'overall_gross_profit': overall_gross_profit,
        'overall_net_profit': overall_net_profit,
    }
    return render(request, 'dairy_erp/finance/profitability.html', context)


@login_required
@require_POST
def calculate_profitability(request):
    """Manually trigger profitability calculation for a specific month"""
    year = int(request.POST.get('year'))
    month = int(request.POST.get('month'))

    # Get income for this month
    income = IncomeRecord.objects.filter(
        date__year=year,
        date__month=month
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Get expenses for this month
    direct_expenses = ExpenseRecord.objects.filter(
        date__year=year,
        date__month=month,
        category__is_direct_cost=True
    ).aggregate(total=Sum('amount'))['total'] or 0

    indirect_expenses = ExpenseRecord.objects.filter(
        date__year=year,
        date__month=month,
        category__is_direct_cost=False
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Calculate profits
    gross_profit = income - direct_expenses
    net_profit = gross_profit - indirect_expenses

    # Update or create profitability record
    profitability, created = Profitability.objects.update_or_create(
        year=year,
        month=month,
        defaults={
            'total_income': income,
            'direct_costs': direct_expenses,
            'indirect_costs': indirect_expenses,
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            # ROI and cash surplus calculations would be more complex
            'roi_percentage': 0,
            'cash_surplus': 0
        }
    )

    messages.success(request, f'Profitability has been calculated for {year}-{month:02d}!')
    return redirect('finance:profitability')


# API ViewSets
class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for ExpenseCategory"""
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class IncomeCategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for IncomeCategory"""
    queryset = IncomeCategory.objects.all()
    serializer_class = IncomeCategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class ExpenseRecordViewSet(viewsets.ModelViewSet):
    """API endpoint for ExpenseRecord"""
    queryset = ExpenseRecord.objects.all()
    serializer_class = ExpenseRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['category', 'date', 'related_buffalo']
    ordering_fields = ['date', 'amount']


class IncomeRecordViewSet(viewsets.ModelViewSet):
    """API endpoint for IncomeRecord"""
    queryset = IncomeRecord.objects.all()
    serializer_class = IncomeRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['category', 'date', 'related_buffalo']
    ordering_fields = ['date', 'total_amount']


class ProfitabilityViewSet(viewsets.ModelViewSet):
    """API endpoint for Profitability"""
    queryset = Profitability.objects.all()
    serializer_class = ProfitabilitySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['year', 'month']
    ordering_fields = ['year', 'month']