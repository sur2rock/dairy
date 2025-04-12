from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
import csv
import io
import datetime

from .models import Buffalo, Breed, LifecycleEvent, MilkProduction
from .forms import BuffaloForm, BreedForm, LifecycleEventForm, MilkProductionForm, MilkProductionBatchForm
from .serializers import BuffaloSerializer, BreedSerializer, LifecycleEventSerializer, MilkProductionSerializer


# Buffalo Views
@login_required
def buffalo_list(request):
    """Display all buffaloes with filtering options"""
    status_filter = request.GET.get('status', '')
    breed_filter = request.GET.get('breed', '')

    buffaloes = Buffalo.objects.all()

    if status_filter:
        buffaloes = buffaloes.filter(status=status_filter)

    if breed_filter:
        buffaloes = buffaloes.filter(breed_id=breed_filter)

    # Summary statistics
    total_count = Buffalo.objects.filter(is_active=True).count()
    milking_count = Buffalo.objects.filter(is_active=True, status='MILKING').count()
    pregnant_count = Buffalo.objects.filter(is_active=True, status='PREGNANT').count()
    dry_count = Buffalo.objects.filter(is_active=True, status='DRY').count()

    # Get all breeds for the filter dropdown
    breeds = Breed.objects.all()

    context = {
        'title': 'Buffalo Management',
        'buffaloes': buffaloes,
        'total_count': total_count,
        'milking_count': milking_count,
        'pregnant_count': pregnant_count,
        'dry_count': dry_count,
        'status_choices': Buffalo.STATUS_CHOICES,
        'breeds': breeds,
        'status_filter': status_filter,
        'breed_filter': breed_filter,
    }
    return render(request, 'dairy_erp/herd/buffalo_list.html', context)


@login_required
def buffalo_detail(request, buffalo_id):
    """Display detailed information about a single buffalo"""
    buffalo = get_object_or_404(Buffalo, id=buffalo_id)

    # Get lifecycle events
    lifecycle_events = buffalo.lifecycle_events.all().order_by('-event_date')

    # Get milk production data (last 30 days)
    last_30_days = timezone.now().date() - datetime.timedelta(days=30)
    milk_records = buffalo.milk_records.filter(date__gte=last_30_days).order_by('-date', '-time_of_day')

    # Calculate milk production statistics
    total_milk = milk_records.aggregate(total=Sum('quantity_litres'))['total'] or 0
    avg_milk_per_day = milk_records.values('date').annotate(daily=Sum('quantity_litres')).aggregate(avg=Avg('daily'))[
                           'avg'] or 0

    # Prepare data for milk production chart
    dates = []
    am_data = []
    pm_data = []

    # Get unique dates in descending order
    unique_dates = milk_records.order_by('-date').values_list('date', flat=True).distinct()

    for date in unique_dates:
        dates.append(date.strftime('%Y-%m-%d'))

        # Get AM and PM values for this date
        am_value = milk_records.filter(date=date, time_of_day='AM').aggregate(val=Sum('quantity_litres'))['val'] or 0
        pm_value = milk_records.filter(date=date, time_of_day='PM').aggregate(val=Sum('quantity_litres'))['val'] or 0

        am_data.append(float(am_value))
        pm_data.append(float(pm_value))

    # Reverse lists so dates are in ascending order for the chart
    dates.reverse()
    am_data.reverse()
    pm_data.reverse()

    context = {
        'title': f'Buffalo: {buffalo}',
        'buffalo': buffalo,
        'lifecycle_events': lifecycle_events,
        'milk_records': milk_records,
        'total_milk': total_milk,
        'avg_milk_per_day': avg_milk_per_day,
        'chart_dates': dates,
        'chart_am_data': am_data,
        'chart_pm_data': pm_data,
    }
    return render(request, 'dairy_erp/herd/buffalo_detail.html', context)


@login_required
def buffalo_add(request):
    """Add a new buffalo"""
    if request.method == 'POST':
        form = BuffaloForm(request.POST, request.FILES)
        if form.is_valid():
            buffalo = form.save()

            # If it's a birth, create a Birth lifecycle event
            if not buffalo.purchase_date:
                LifecycleEvent.objects.create(
                    buffalo=buffalo,
                    event_type='BIRTH',
                    event_date=buffalo.date_of_birth,
                    notes=f"Born on farm. Initial record creation."
                )
            else:
                # If it's a purchase, create a Purchase lifecycle event
                LifecycleEvent.objects.create(
                    buffalo=buffalo,
                    event_type='PURCHASE',
                    event_date=buffalo.purchase_date,
                    notes=f"Purchased at {buffalo.purchase_price}. Initial record creation."
                )

            messages.success(request, f'Buffalo {buffalo} has been added successfully!')
            return redirect('herd:buffalo_detail', buffalo_id=buffalo.id)
    else:
        form = BuffaloForm()

    context = {
        'title': 'Add Buffalo',
        'form': form,
    }
    return render(request, 'dairy_erp/herd/buffalo_form.html', context)


@login_required
def buffalo_edit(request, buffalo_id):
    """Edit an existing buffalo"""
    buffalo = get_object_or_404(Buffalo, id=buffalo_id)

    if request.method == 'POST':
        form = BuffaloForm(request.POST, request.FILES, instance=buffalo)
        if form.is_valid():
            form.save()
            messages.success(request, f'Buffalo {buffalo} has been updated successfully!')
            return redirect('herd:buffalo_detail', buffalo_id=buffalo.id)
    else:
        form = BuffaloForm(instance=buffalo)

    context = {
        'title': 'Edit Buffalo',
        'form': form,
        'buffalo': buffalo,
    }
    return render(request, 'dairy_erp/herd/buffalo_form.html', context)


@login_required
def buffalo_delete(request, buffalo_id):
    """Delete a buffalo (mark as inactive)"""
    buffalo = get_object_or_404(Buffalo, id=buffalo_id)

    if request.method == 'POST':
        buffalo.is_active = False

        # Check if we need to create a DEATH or SALE lifecycle event
        event_type = request.POST.get('event_type')
        event_date = request.POST.get('event_date')
        notes = request.POST.get('notes', '')

        if event_type and event_date:
            LifecycleEvent.objects.create(
                buffalo=buffalo,
                event_type=event_type,
                event_date=event_date,
                notes=notes
            )

        buffalo.save()
        messages.success(request, f'Buffalo {buffalo} has been removed from active inventory!')
        return redirect('herd:buffalo_list')

    context = {
        'title': 'Remove Buffalo',
        'buffalo': buffalo,
    }
    return render(request, 'dairy_erp/herd/buffalo_delete.html', context)


# Breed Views
@login_required
def breed_list(request):
    """Display all breeds"""
    breeds = Breed.objects.all()

    # Count buffaloes per breed
    for breed in breeds:
        breed.buffalo_count = Buffalo.objects.filter(breed=breed).count()

    context = {
        'title': 'Breeds',
        'breeds': breeds,
    }
    return render(request, 'dairy_erp/herd/breed_list.html', context)


@login_required
def breed_add(request):
    """Add a new breed"""
    if request.method == 'POST':
        form = BreedForm(request.POST)
        if form.is_valid():
            breed = form.save()
            messages.success(request, f'Breed {breed.name} has been added successfully!')
            return redirect('herd:breed_list')
    else:
        form = BreedForm()

    context = {
        'title': 'Add Breed',
        'form': form,
    }
    return render(request, 'dairy_erp/herd/breed_form.html', context)


@login_required
def breed_edit(request, breed_id):
    """Edit an existing breed"""
    breed = get_object_or_404(Breed, id=breed_id)

    if request.method == 'POST':
        form = BreedForm(request.POST, instance=breed)
        if form.is_valid():
            form.save()
            messages.success(request, f'Breed {breed.name} has been updated successfully!')
            return redirect('herd:breed_list')
    else:
        form = BreedForm(instance=breed)

    context = {
        'title': 'Edit Breed',
        'form': form,
        'breed': breed,
    }
    return render(request, 'dairy_erp/herd/breed_form.html', context)


# Lifecycle Event Views
@login_required
def lifecycle_event_add(request):
    """Add a new lifecycle event"""
    if request.method == 'POST':
        form = LifecycleEventForm(request.POST)
        if form.is_valid():
            event = form.save()
            messages.success(request, f'Lifecycle event for {event.buffalo} has been recorded successfully!')
            return redirect('herd:buffalo_detail', buffalo_id=event.buffalo.id)
    else:
        # Pre-select buffalo if passed in URL
        buffalo_id = request.GET.get('buffalo_id')
        if buffalo_id:
            try:
                buffalo = Buffalo.objects.get(id=buffalo_id)
                form = LifecycleEventForm(initial={'buffalo': buffalo, 'event_date': timezone.now().date()})
            except Buffalo.DoesNotExist:
                form = LifecycleEventForm(initial={'event_date': timezone.now().date()})
        else:
            form = LifecycleEventForm(initial={'event_date': timezone.now().date()})

    context = {
        'title': 'Record Lifecycle Event',
        'form': form,
    }
    return render(request, 'dairy_erp/herd/lifecycle_event_form.html', context)


# Milk Production Views
@login_required
def milk_production_list(request):
    """Display milk production records with filtering options"""
    today = timezone.now().date()
    start_date = request.GET.get('start_date', (today - datetime.timedelta(days=7)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    buffalo_id = request.GET.get('buffalo_id', '')

    milk_records = MilkProduction.objects.all()

    if start_date:
        milk_records = milk_records.filter(date__gte=start_date)

    if end_date:
        milk_records = milk_records.filter(date__lte=end_date)

    if buffalo_id:
        milk_records = milk_records.filter(buffalo_id=buffalo_id)

    # Get all active, milking buffaloes for the filter dropdown
    milking_buffaloes = Buffalo.objects.filter(is_active=True, status='MILKING')

    # Calculate totals
    total_milk = milk_records.aggregate(total=Sum('quantity_litres'))['total'] or 0
    daily_avg = milk_records.values('date').annotate(daily=Sum('quantity_litres')).aggregate(avg=Avg('daily'))[
                    'avg'] or 0

    # Prepare data for milk production chart
    chart_data = milk_records.values('date').annotate(
        total=Sum('quantity_litres')
    ).order_by('date')

    chart_dates = [entry['date'].strftime('%Y-%m-%d') for entry in chart_data]
    chart_values = [float(entry['total']) for entry in chart_data]

    context = {
        'title': 'Milk Production',
        'milk_records': milk_records,
        'milking_buffaloes': milking_buffaloes,
        'start_date': start_date,
        'end_date': end_date,
        'buffalo_id': buffalo_id,
        'total_milk': total_milk,
        'daily_avg': daily_avg,
        'chart_dates': chart_dates,
        'chart_values': chart_values,
    }
    return render(request, 'dairy_erp/herd/milk_production_list.html', context)


@login_required
def milk_production_add(request):
    """Add a new milk production record"""
    if request.method == 'POST':
        form = MilkProductionForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, f'Milk production record for {record.buffalo} has been added successfully!')
            return redirect('herd:milk_production_list')
    else:
        # Pre-select buffalo if passed in URL
        buffalo_id = request.GET.get('buffalo_id')
        if buffalo_id:
            try:
                buffalo = Buffalo.objects.get(id=buffalo_id)
                form = MilkProductionForm(initial={'buffalo': buffalo, 'date': timezone.now().date()})
            except Buffalo.DoesNotExist:
                form = MilkProductionForm(initial={'date': timezone.now().date()})
        else:
            form = MilkProductionForm(initial={'date': timezone.now().date()})

    context = {
        'title': 'Record Milk Production',
        'form': form,
    }
    return render(request, 'dairy_erp/herd/milk_production_form.html', context)


@login_required
def milk_production_batch(request):
    """Add milk production records for multiple buffaloes at once"""
    if request.method == 'POST':
        form = MilkProductionBatchForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data['date']
            time_of_day = form.cleaned_data['time_of_day']
            records_created = 0

            # Process the data for each buffalo
            for key, value in form.cleaned_data.items():
                if key.startswith('buffalo_') and value:
                    buffalo_id = int(key.split('_')[1])
                    try:
                        buffalo = Buffalo.objects.get(id=buffalo_id)

                        # Check if record already exists
                        record, created = MilkProduction.objects.update_or_create(
                            buffalo=buffalo,
                            date=date,
                            time_of_day=time_of_day,
                            defaults={'quantity_litres': value}
                        )

                        if created:
                            records_created += 1
                    except Buffalo.DoesNotExist:
                        pass

            messages.success(request, f'{records_created} milk production records have been added/updated!')
            return redirect('herd:milk_production_list')
    else:
        form = MilkProductionBatchForm(initial={'date': timezone.now().date()})

    context = {
        'title': 'Batch Record Milk Production',
        'form': form,
    }
    return render(request, 'dairy_erp/herd/milk_production_batch_form.html', context)


@login_required
def export_milk_production(request):
    """Export milk production data to CSV"""
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    milk_records = MilkProduction.objects.all()

    if start_date:
        milk_records = milk_records.filter(date__gte=start_date)

    if end_date:
        milk_records = milk_records.filter(date__lte=end_date)

    # Create CSV file
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Write header row
    writer.writerow(['Date', 'Time', 'Buffalo ID', 'Buffalo Name', 'Quantity (L)', 'Somatic Cell Count', 'Notes'])

    # Write data rows
    for record in milk_records:
        writer.writerow([
            record.date,
            record.get_time_of_day_display(),
            record.buffalo.buffalo_id,
            record.buffalo.name or '',
            record.quantity_litres,
            record.somatic_cell_count or '',
            record.notes or ''
        ])

    # Prepare response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='text/csv')
    response[
        'Content-Disposition'] = f'attachment; filename="milk_production_export_{timezone.now().strftime("%Y_%m_%d")}.csv"'

    return response


# API ViewSets
class BreedViewSet(viewsets.ModelViewSet):
    """API endpoint for Breed"""
    queryset = Breed.objects.all()
    serializer_class = BreedSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class BuffaloViewSet(viewsets.ModelViewSet):
    """API endpoint for Buffalo"""
    queryset = Buffalo.objects.all()
    serializer_class = BuffaloSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'breed', 'gender', 'is_active']
    search_fields = ['buffalo_id', 'name']
    ordering_fields = ['date_of_birth', 'status', 'lactation_number']

    @action(detail=True, methods=['get'])
    def lifecycle(self, request, pk=None):
        """Return all lifecycle events for a specific buffalo"""
        buffalo = self.get_object()
        events = buffalo.lifecycle_events.all()
        serializer = LifecycleEventSerializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def milking(self, request, pk=None):
        """Return all milk production records for a specific buffalo"""
        buffalo = self.get_object()
        records = buffalo.milk_records.all()

        # Apply date filters if provided
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)

        if start_date:
            records = records.filter(date__gte=start_date)

        if end_date:
            records = records.filter(date__lte=end_date)

        serializer = MilkProductionSerializer(records, many=True)
        return Response(serializer.data)


class LifecycleEventViewSet(viewsets.ModelViewSet):
    """API endpoint for LifecycleEvent"""
    queryset = LifecycleEvent.objects.all()
    serializer_class = LifecycleEventSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['buffalo', 'event_type']
    ordering_fields = ['event_date']


class MilkProductionViewSet(viewsets.ModelViewSet):
    """API endpoint for MilkProduction"""
    queryset = MilkProduction.objects.all()
    serializer_class = MilkProductionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['buffalo', 'date', 'time_of_day']
    ordering_fields = ['date', 'time_of_day']