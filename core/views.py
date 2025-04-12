from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required


@login_required
def dashboard(request):
    """Main dashboard view"""
    # Import module models inside the function to avoid circular imports
    from herd.models import Buffalo, MilkProduction
    from django.db.models import Sum, Avg
    import datetime
    from django.utils import timezone

    # Get herd summary data
    total_buffalo = Buffalo.objects.filter(is_active=True).count()
    milking_buffalo = Buffalo.objects.filter(is_active=True, status='MILKING').count()
    dry_buffalo = Buffalo.objects.filter(is_active=True, status='DRY').count()
    pregnant_buffalo = Buffalo.objects.filter(is_active=True, status='PREGNANT').count()

    # Get milk production data for the last 7 days
    seven_days_ago = timezone.now().date() - datetime.timedelta(days=7)
    milk_production = MilkProduction.objects.filter(date__gte=seven_days_ago)

    # Calculate daily milk production for the chart
    daily_milk = milk_production.values('date').annotate(total=Sum('quantity_litres')).order_by('date')

    milk_dates = [entry['date'].strftime('%Y-%m-%d') for entry in daily_milk]
    milk_values = [float(entry['total']) for entry in daily_milk]

    # Calculate total and average milk production
    total_milk = milk_production.aggregate(total=Sum('quantity_litres'))['total'] or 0
    avg_milk_per_day = 0
    if milk_dates:
        avg_milk_per_day = total_milk / len(milk_dates)

    # Compute the remaining buffalo count
    remaining_buffalo = total_buffalo - milking_buffalo - dry_buffalo - pregnant_buffalo

    context = {
        'title': 'Dashboard',
        'total_buffalo': total_buffalo,
        'milking_buffalo': milking_buffalo,
        'dry_buffalo': dry_buffalo,
        'pregnant_buffalo': pregnant_buffalo,
        'total_milk': total_milk,
        'avg_milk_per_day': avg_milk_per_day,
        'milk_dates': milk_dates,
        'milk_values': milk_values,
        'remaining_buffalo': remaining_buffalo,

    }
    return render(request, 'dairy_erp/dashboard.html', context)


def login_view(request):
    """User login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'dairy_erp/login.html', {'title': 'Login'})


def logout_view(request):
    """User logout view"""
    logout(request)
    return redirect('core:login')