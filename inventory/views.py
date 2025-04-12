from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
import csv
import io
import json
import datetime

from .models import FodderType, FeedInventory, FeedPurchase, FeedConsumption, InHouseFeedProduction
from .forms import FodderTypeForm, FeedInventoryForm, FeedPurchaseForm, FeedConsumptionForm, InHouseFeedProductionForm
from .serializers import FodderTypeSerializer, FeedInventorySerializer, FeedPurchaseSerializer, \
    FeedConsumptionSerializer, InHouseFeedProductionSerializer
from finance.models import ExpenseCategory, ExpenseRecord
from configuration.models import GlobalSettings


# Fodder Type Views
@login_required
def fodder_type_list(request):
    """Display all fodder types"""
    fodder_types = FodderType.objects.all().order_by('name')

    # Try to get the inventory for each fodder type
    for fodder_type in fodder_types:
        try:
            fodder_type.current_inventory = fodder_type.inventory.quantity_on_hand
        except FeedInventory.DoesNotExist:
            fodder_type.current_inventory = 0

    context = {
        'title': 'Feed Types',
        'fodder_types': fodder_types,
    }
    return render(request, 'dairy_erp/inventory/fodder_type_list.html', context)


@login_required
def fodder_type_add(request):
    """Add a new fodder type"""
    if request.method == 'POST':
        form = FodderTypeForm(request.POST)
        if form.is_valid():
            fodder_type = form.save()

            # Create initial inventory record with zero quantity
            FeedInventory.objects.create(
                fodder_type=fodder_type,
                quantity_on_hand=0
            )

            messages.success(request, f'Feed type {fodder_type.name} has been added successfully!')
            return redirect('inventory:fodder_type_list')
    else:
        form = FodderTypeForm()

    context = {
        'title': 'Add Feed Type',
        'form': form,
    }
    return render(request, 'dairy_erp/inventory/fodder_type_form.html', context)


@login_required
def fodder_type_edit(request, fodder_type_id):
    """Edit an existing fodder type"""
    fodder_type = get_object_or_404(FodderType, id=fodder_type_id)

    if request.method == 'POST':
        form = FodderTypeForm(request.POST, instance=fodder_type)
        if form.is_valid():
            form.save()
            messages.success(request, f'Feed type {fodder_type.name} has been updated successfully!')
            return redirect('inventory:fodder_type_list')
    else:
        form = FodderTypeForm(instance=fodder_type)

    context = {
        'title': 'Edit Feed Type',
        'form': form,
        'fodder_type': fodder_type,
    }
    return render(request, 'dairy_erp/inventory/fodder_type_form.html', context)


@login_required
def fodder_type_detail(request, fodder_type_id):
    """Display detailed information about a fodder type"""
    fodder_type = get_object_or_404(FodderType, id=fodder_type_id)

    # Get inventory
    try:
        inventory = fodder_type.inventory
    except FeedInventory.DoesNotExist:
        inventory = FeedInventory.objects.create(
            fodder_type=fodder_type,
            quantity_on_hand=0
        )

    # Get recent purchases
    purchases = FeedPurchase.objects.filter(fodder_type=fodder_type).order_by('-date')[:10]

    # Get recent consumption
    consumption = FeedConsumption.objects.filter(fodder_type=fodder_type).order_by('-date')[:10]

    # Get recent production (if applicable)
    production = None
    if fodder_type.is_produced_in_house:
        production = InHouseFeedProduction.objects.filter(fodder_type=fodder_type).order_by('-date')[:10]

    # Calculate statistics
    total_purchased = FeedPurchase.objects.filter(fodder_type=fodder_type).aggregate(
        total=Sum('quantity_purchased')
    )['total'] or 0

    total_cost = FeedPurchase.objects.filter(fodder_type=fodder_type).aggregate(
        total=Sum('total_cost')
    )['total'] or 0

    total_consumed = FeedConsumption.objects.filter(fodder_type=fodder_type).aggregate(
        total=Sum('quantity_consumed')
    )['total'] or 0

    total_produced = 0
    if fodder_type.is_produced_in_house:
        total_produced = InHouseFeedProduction.objects.filter(fodder_type=fodder_type).aggregate(
            total=Sum('quantity_produced')
        )['total'] or 0

    context = {
        'title': f'Feed Type: {fodder_type.name}',
        'fodder_type': fodder_type,
        'inventory': inventory,
        'purchases': purchases,
        'consumption': consumption,
        'production': production,
        'total_purchased': total_purchased,
        'total_cost': total_cost,
        'total_consumed': total_consumed,
        'total_produced': total_produced,
    }
    return render(request, 'dairy_erp/inventory/fodder_type_detail.html', context)


# Inventory Views
@login_required
def inventory_list(request):
    """Display current inventory levels"""
    inventory_items = FeedInventory.objects.all().select_related('fodder_type')

    # Create a chart of inventory levels
    chart_labels = [item.fodder_type.name for item in inventory_items]
    chart_values = [float(item.quantity_on_hand) for item in inventory_items]
    chart_units = [item.fodder_type.unit for item in inventory_items]

    context = {
        'title': 'Feed Inventory',
        'inventory_items': inventory_items,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
        'chart_units': json.dumps(chart_units),
    }
    return render(request, 'dairy_erp/inventory/inventory_list.html', context)


@login_required
def inventory_adjust(request, inventory_id):
    """Adjust inventory level manually"""
    inventory = get_object_or_404(FeedInventory, id=inventory_id)

    if request.method == 'POST':
        form = FeedInventoryForm(request.POST, instance=inventory)
        if form.is_valid():
            form.save()
            messages.success(request,
                             f'Inventory level for {inventory.fodder_type.name} has been adjusted successfully!')
            return redirect('inventory:inventory_list')
    else:
        form = FeedInventoryForm(instance=inventory)

    context = {
        'title': f'Adjust Inventory: {inventory.fodder_type.name}',
        'form': form,
        'inventory': inventory,
    }
    return render(request, 'dairy_erp/inventory/inventory_form.html', context)


# Purchase Views
@login_required
def purchase_list(request):
    """Display feed purchase records"""
    today = timezone.now().date()
    start_date = request.GET.get('start_date', (today - datetime.timedelta(days=30)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    fodder_type_id = request.GET.get('fodder_type_id', '')

    purchases = FeedPurchase.objects.all().select_related('fodder_type')

    if start_date:
        purchases = purchases.filter(date__gte=start_date)

    if end_date:
        purchases = purchases.filter(date__lte=end_date)

    if fodder_type_id:
        purchases = purchases.filter(fodder_type_id=fodder_type_id)

    # Get fodder types for filter dropdown
    fodder_types = FodderType.objects.all()

    # Calculate totals
    total_quantity = purchases.aggregate(
        total=Sum(ExpressionWrapper(
            F('quantity_purchased'),
            output_field=DecimalField()
        ))
    )['total'] or 0

    total_cost = purchases.aggregate(total=Sum('total_cost'))['total'] or 0

    # Prepare chart data - purchases by feed type
    purchase_by_type = purchases.values('fodder_type__name').annotate(
        total=Sum('total_cost')
    ).order_by('-total')

    chart_labels = [item['fodder_type__name'] for item in purchase_by_type]
    chart_values = [float(item['total']) for item in purchase_by_type]

    context = {
        'title': 'Feed Purchases',
        'purchases': purchases,
        'fodder_types': fodder_types,
        'start_date': start_date,
        'end_date': end_date,
        'fodder_type_id': fodder_type_id,
        'total_quantity': total_quantity,
        'total_cost': total_cost,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
    }
    return render(request, 'dairy_erp/inventory/purchase_list.html', context)


@login_required
def purchase_add(request):
    """Add a new feed purchase"""
    if request.method == 'POST':
        form = FeedPurchaseForm(request.POST)
        if form.is_valid():
            purchase = form.save()

            # Update inventory
            fodder_type = purchase.fodder_type
            try:
                inventory = fodder_type.inventory
                inventory.quantity_on_hand += purchase.quantity_purchased
                inventory.save()
            except FeedInventory.DoesNotExist:
                inventory = FeedInventory.objects.create(
                    fodder_type=fodder_type,
                    quantity_on_hand=purchase.quantity_purchased
                )

            # Update fodder type cost per unit (simple avg)
            fodder_type.current_cost_per_unit = purchase.cost_per_unit
            fodder_type.save()

            messages.success(request, f'Feed purchase has been recorded successfully!')
            return redirect('inventory:purchase_list')
    else:
        form = FeedPurchaseForm(initial={'date': timezone.now().date()})

    context = {
        'title': 'Add Feed Purchase',
        'form': form,
    }
    return render(request, 'dairy_erp/inventory/purchase_form.html', context)


@login_required
def purchase_edit(request, purchase_id):
    """Edit an existing feed purchase"""
    purchase = get_object_or_404(FeedPurchase, id=purchase_id)
    old_quantity = purchase.quantity_purchased

    if request.method == 'POST':
        form = FeedPurchaseForm(request.POST, instance=purchase)
        if form.is_valid():
            purchase = form.save()

            # Update inventory for the difference in quantity
            if old_quantity != purchase.quantity_purchased:
                quantity_diff = purchase.quantity_purchased - old_quantity
                try:
                    inventory = purchase.fodder_type.inventory
                    inventory.quantity_on_hand += quantity_diff
                    inventory.save()
                except FeedInventory.DoesNotExist:
                    inventory = FeedInventory.objects.create(
                        fodder_type=purchase.fodder_type,
                        quantity_on_hand=purchase.quantity_purchased
                    )

            # Update expense record if it exists
            if purchase.related_expense:
                expense = purchase.related_expense
                expense.date = purchase.date
                expense.amount = purchase.total_cost
                expense.description = f"Purchase of {purchase.quantity_purchased} {purchase.fodder_type.unit} of {purchase.fodder_type.name}"
                expense.supplier_vendor = purchase.supplier
                expense.notes = purchase.notes
                expense.save()

            messages.success(request, f'Feed purchase has been updated successfully!')
            return redirect('inventory:purchase_list')
    else:
        form = FeedPurchaseForm(instance=purchase)

    context = {
        'title': 'Edit Feed Purchase',
        'form': form,
        'purchase': purchase,
    }
    return render(request, 'dairy_erp/inventory/purchase_form.html', context)


@login_required
def purchase_delete(request, purchase_id):
    """Delete a feed purchase"""
    purchase = get_object_or_404(FeedPurchase, id=purchase_id)

    if request.method == 'POST':
        # Update inventory
        try:
            inventory = purchase.fodder_type.inventory
            inventory.quantity_on_hand -= purchase.quantity_purchased
            inventory.save()
        except FeedInventory.DoesNotExist:
            pass

        # If there's a related expense, delete it
        if purchase.related_expense:
            purchase.related_expense.delete()

        purchase.delete()
        messages.success(request, f'Feed purchase has been deleted successfully!')
        return redirect('inventory:purchase_list')

    context = {
        'title': 'Delete Feed Purchase',
        'purchase': purchase,
    }
    return render(request, 'dairy_erp/inventory/purchase_delete.html', context)


# Consumption Views
@login_required
def consumption_list(request):
    """Display feed consumption records"""
    today = timezone.now().date()
    start_date = request.GET.get('start_date', (today - datetime.timedelta(days=30)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    fodder_type_id = request.GET.get('fodder_type_id', '')

    consumption_records = FeedConsumption.objects.all().select_related('fodder_type', 'buffalo')

    if start_date:
        consumption_records = consumption_records.filter(date__gte=start_date)

    if end_date:
        consumption_records = consumption_records.filter(date__lte=end_date)

    if fodder_type_id:
        consumption_records = consumption_records.filter(fodder_type_id=fodder_type_id)

    # Get fodder types for filter dropdown
    fodder_types = FodderType.objects.all()

    # Calculate totals
    total_consumed = consumption_records.aggregate(
        total=Sum(ExpressionWrapper(
            F('quantity_consumed'),
            output_field=DecimalField()
        ))
    )['total'] or 0

    # Prepare chart data - consumption by feed type
    consumption_by_type = consumption_records.values('fodder_type__name').annotate(
        total=Sum('quantity_consumed')
    ).order_by('-total')

    chart_labels = [item['fodder_type__name'] for item in consumption_by_type]
    chart_values = [float(item['total']) for item in consumption_by_type]

    context = {
        'title': 'Feed Consumption',
        'consumption_records': consumption_records,
        'fodder_types': fodder_types,
        'start_date': start_date,
        'end_date': end_date,
        'fodder_type_id': fodder_type_id,
        'total_consumed': total_consumed,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
    }
    return render(request, 'dairy_erp/inventory/consumption_list.html', context)


@login_required
def consumption_add(request):
    """Add a new feed consumption record"""
    if request.method == 'POST':
        form = FeedConsumptionForm(request.POST)
        if form.is_valid():
            consumption = form.save()

            # Update inventory
            fodder_type = consumption.fodder_type
            try:
                inventory = fodder_type.inventory
                inventory.quantity_on_hand -= consumption.quantity_consumed
                inventory.save()
            except FeedInventory.DoesNotExist:
                inventory = FeedInventory.objects.create(
                    fodder_type=fodder_type,
                    quantity_on_hand=-consumption.quantity_consumed
                )

            messages.success(request, f'Feed consumption has been recorded successfully!')
            return redirect('inventory:consumption_list')
    else:
        form = FeedConsumptionForm(initial={'date': timezone.now().date()})

    context = {
        'title': 'Add Feed Consumption',
        'form': form,
    }
    return render(request, 'dairy_erp/inventory/consumption_form.html', context)


@login_required
def consumption_edit(request, consumption_id):
    """Edit an existing feed consumption record"""
    consumption = get_object_or_404(FeedConsumption, id=consumption_id)
    old_quantity = consumption.quantity_consumed

    if request.method == 'POST':
        form = FeedConsumptionForm(request.POST, instance=consumption)
        if form.is_valid():
            consumption = form.save()

            # Update inventory for the difference in quantity
            if old_quantity != consumption.quantity_consumed:
                quantity_diff = old_quantity - consumption.quantity_consumed
                try:
                    inventory = consumption.fodder_type.inventory
                    inventory.quantity_on_hand += quantity_diff
                    inventory.save()
                except FeedInventory.DoesNotExist:
                    inventory = FeedInventory.objects.create(
                        fodder_type=consumption.fodder_type,
                        quantity_on_hand=-consumption.quantity_consumed
                    )

            messages.success(request, f'Feed consumption has been updated successfully!')
            return redirect('inventory:consumption_list')
    else:
        form = FeedConsumptionForm(instance=consumption)

    context = {
        'title': 'Edit Feed Consumption',
        'form': form,
        'consumption': consumption,
    }
    return render(request, 'dairy_erp/inventory/consumption_form.html', context)


@login_required
def consumption_delete(request, consumption_id):
    """Delete a feed consumption record"""
    consumption = get_object_or_404(FeedConsumption, id=consumption_id)

    if request.method == 'POST':
        # Update inventory
        try:
            inventory = consumption.fodder_type.inventory
            inventory.quantity_on_hand += consumption.quantity_consumed
            inventory.save()
        except FeedInventory.DoesNotExist:
            pass

        consumption.delete()
        messages.success(request, f'Feed consumption has been deleted successfully!')
        return redirect('inventory:consumption_list')

    context = {
        'title': 'Delete Feed Consumption',
        'consumption': consumption,
    }
    return render(request, 'dairy_erp/inventory/consumption_delete.html', context)


# In-House Production Views
@login_required
def production_list(request):
    """Display in-house feed production records"""
    today = timezone.now().date()
    start_date = request.GET.get('start_date', (today - datetime.timedelta(days=30)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    fodder_type_id = request.GET.get('fodder_type_id', '')

    production_records = InHouseFeedProduction.objects.all().select_related('fodder_type')

    if start_date:
        production_records = production_records.filter(date__gte=start_date)

    if end_date:
        production_records = production_records.filter(date__lte=end_date)

    if fodder_type_id:
        production_records = production_records.filter(fodder_type_id=fodder_type_id)

    # Get fodder types for filter dropdown (only those that can be produced in-house)
    fodder_types = FodderType.objects.filter(is_produced_in_house=True)

    # Calculate totals
    total_produced = production_records.aggregate(
        total=Sum(ExpressionWrapper(
            F('quantity_produced'),
            output_field=DecimalField()
        ))
    )['total'] or 0

    total_cost = production_records.aggregate(total=Sum('total_production_cost'))['total'] or 0

    # Prepare chart data - production by feed type
    production_by_type = production_records.values('fodder_type__name').annotate(
        total=Sum('quantity_produced')
    ).order_by('-total')

    chart_labels = [item['fodder_type__name'] for item in production_by_type]
    chart_values = [float(item['total']) for item in production_by_type]

    context = {
        'title': 'In-House Feed Production',
        'production_records': production_records,
        'fodder_types': fodder_types,
        'start_date': start_date,
        'end_date': end_date,
        'fodder_type_id': fodder_type_id,
        'total_produced': total_produced,
        'total_cost': total_cost,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
    }
    return render(request, 'dairy_erp/inventory/production_list.html', context)


@login_required
def production_add(request):
    """Add a new in-house feed production record"""
    if request.method == 'POST':
        form = InHouseFeedProductionForm(request.POST)
        if form.is_valid():
            production = form.save()

            # Update inventory
            fodder_type = production.fodder_type
            try:
                inventory = fodder_type.inventory
                inventory.quantity_on_hand += production.quantity_produced
                inventory.save()
            except FeedInventory.DoesNotExist:
                inventory = FeedInventory.objects.create(
                    fodder_type=fodder_type,
                    quantity_on_hand=production.quantity_produced
                )

            # Update fodder type cost per unit based on this production
            fodder_type.current_cost_per_unit = production.cost_per_unit
            fodder_type.save()

            messages.success(request, f'Feed production has been recorded successfully!')
            return redirect('inventory:production_list')
    else:
        form = InHouseFeedProductionForm(initial={'date': timezone.now().date()})

    context = {
        'title': 'Add Feed Production',
        'form': form,
    }
    return render(request, 'dairy_erp/inventory/production_form.html', context)


@login_required
def production_edit(request, production_id):
    """Edit an existing in-house feed production record"""
    production = get_object_or_404(InHouseFeedProduction, id=production_id)
    old_quantity = production.quantity_produced

    if request.method == 'POST':
        form = InHouseFeedProductionForm(request.POST, instance=production)
        if form.is_valid():
            production = form.save()

            # Update inventory for the difference in quantity
            if old_quantity != production.quantity_produced:
                quantity_diff = production.quantity_produced - old_quantity
                try:
                    inventory = production.fodder_type.inventory
                    inventory.quantity_on_hand += quantity_diff
                    inventory.save()
                except FeedInventory.DoesNotExist:
                    inventory = FeedInventory.objects.create(
                        fodder_type=production.fodder_type,
                        quantity_on_hand=production.quantity_produced
                    )

            messages.success(request, f'Feed production has been updated successfully!')
            return redirect('inventory:production_list')
    else:
        form = InHouseFeedProductionForm(instance=production)

    context = {
        'title': 'Edit Feed Production',
        'form': form,
        'production': production,
    }
    return render(request, 'dairy_erp/inventory/production_form.html', context)


@login_required
def production_delete(request, production_id):
    """Delete an in-house feed production record"""
    production = get_object_or_404(InHouseFeedProduction, id=production_id)

    if request.method == 'POST':
        # Update inventory
        try:
            inventory = production.fodder_type.inventory
            inventory.quantity_on_hand -= production.quantity_produced
            inventory.save()
        except FeedInventory.DoesNotExist:
            pass

        production.delete()
        messages.success(request, f'Feed production has been deleted successfully!')
        return redirect('inventory:production_list')

    context = {
        'title': 'Delete Feed Production',
        'production': production,
    }
    return render(request, 'dairy_erp/inventory/production_delete.html', context)


# API ViewSets
class FodderTypeViewSet(viewsets.ModelViewSet):
    """API endpoint for FodderType"""
    queryset = FodderType.objects.all()
    serializer_class = FodderTypeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'category']


class FeedInventoryViewSet(viewsets.ModelViewSet):
    """API endpoint for FeedInventory"""
    queryset = FeedInventory.objects.all()
    serializer_class = FeedInventorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['fodder_type']


class FeedPurchaseViewSet(viewsets.ModelViewSet):
    """API endpoint for FeedPurchase"""
    queryset = FeedPurchase.objects.all()
    serializer_class = FeedPurchaseSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['fodder_type', 'date']
    ordering_fields = ['date', 'total_cost']


class FeedConsumptionViewSet(viewsets.ModelViewSet):
    """API endpoint for FeedConsumption"""
    queryset = FeedConsumption.objects.all()
    serializer_class = FeedConsumptionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['fodder_type', 'date', 'consumed_by', 'buffalo']
    ordering_fields = ['date', 'quantity_consumed']


class InHouseFeedProductionViewSet(viewsets.ModelViewSet):
    """API endpoint for InHouseFeedProduction"""
    queryset = InHouseFeedProduction.objects.all()
    serializer_class = InHouseFeedProductionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['fodder_type', 'date']
    ordering_fields = ['date', 'quantity_produced']