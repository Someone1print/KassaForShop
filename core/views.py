from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q, Case, When, F, DecimalField
from django.db.models.functions import Coalesce
from django.db import models
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from core.models import Product, Shift, Receipt, ReceiptItem, PaymentSettings, UserLoginLog
from core.services.shift_service import ShiftService
from core.forms import RegistrationForm


def register_view(request):
    """Регистрация нового пользователя"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('dashboard')
    else:
        form = RegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    """Страница входа"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Рекомендуется использовать встроенные механизмы Django для предотвращения атак
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('dashboard')
            else:
                error = 'Аккаунт заблокирован'
        else:
            # Сигналы в signals.py запишут неудачную попытку
            error = 'Неверный логин или пароль'
    
    return render(request, 'registration/login.html', {'error': error})


def logout_view(request):
    """Выход из системы"""
    logout(request)
    return redirect('login')


def favicon_view(request):
    """Обработка favicon для избежания 404"""
    from django.http import HttpResponse
    # Возвращаем пустой ответ или SVG favicon
    svg_icon = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <text y=".9em" font-size="90">💰</text>
    </svg>'''
    return HttpResponse(svg_icon, content_type='image/svg+xml')


@login_required
def dashboard(request):
    """Главная страница (Dashboard)"""
    user = request.user
    is_admin = user.is_staff or user.is_superuser
    
    # Статистика для кассира
    if not is_admin:
        current_shift = ShiftService.get_current_shift(user)
        today_shifts = Shift.objects.filter(cashier=user, opened_at__date=timezone.now().date())
        today_receipts = Receipt.objects.filter(
            cashier=user,
            created_at__date=timezone.now().date()
        )
        today_total = today_receipts.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        context = {
            'current_shift': current_shift,
            'today_shifts_count': today_shifts.count(),
            'today_receipts_count': today_receipts.count(),
            'today_total': today_total,
        }
    else:
        # Статистика для админа
        today_receipts = Receipt.objects.filter(created_at__date=timezone.now().date())
        today_total = today_receipts.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        active_shifts = Shift.objects.filter(status=Shift.STATUS_OPEN).count()
        total_cashiers = User.objects.filter(is_staff=False, is_superuser=False).count()
        
        # Выручка за последние 7 дней
        last_7_days = []
        for i in range(6, -1, -1):
            date = timezone.now().date() - timedelta(days=i)
            day_total = Receipt.objects.filter(
                created_at__date=date,
                receipt_type=Receipt.RECEIPT_SALE
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            last_7_days.append({
                'date': date.strftime('%d.%m'),
                'total': float(day_total)
            })
        
        # Топ товаров
        top_products = ReceiptItem.objects.filter(
            receipt__receipt_type=Receipt.RECEIPT_SALE,
            receipt__created_at__date__gte=timezone.now().date() - timedelta(days=7)
        ).values('product__name').annotate(
            total_qty=Sum('qty'),
            total_amount=Sum('line_total')
        ).order_by('-total_qty')[:10]
        
        context = {
            'today_receipts_count': today_receipts.count(),
            'today_total': today_total,
            'active_shifts': active_shifts,
            'total_cashiers': total_cashiers,
            'last_7_days': json.dumps(last_7_days),
            'top_products': top_products,
        }
    
    context['is_admin'] = is_admin
    return render(request, 'core/dashboard.html', context)


@login_required
def pos_view(request):
    """Кассовый экран"""
    current_shift = ShiftService.get_current_shift(request.user)
    if not current_shift:
        return redirect('shift_open')
    
    payment_settings = PaymentSettings.get_settings()
    
    return render(request, 'core/pos.html', {
        'current_shift': current_shift,
        'payment_settings': payment_settings
    })


@login_required
def shifts_list(request):
    """Список смен"""
    user = request.user
    is_admin = user.is_staff or user.is_superuser
    
    if is_admin:
        shifts = Shift.objects.all()
        cashier_id = request.GET.get('cashier_id')
        if cashier_id:
            shifts = shifts.filter(cashier_id=cashier_id)
    else:
        shifts = Shift.objects.filter(cashier=user)
    
    return render(request, 'core/shifts_list.html', {
        'shifts': shifts,
        'is_admin': is_admin
    })


@login_required
def shift_detail(request, shift_id):
    """Детали смены"""
    shift = get_object_or_404(Shift, id=shift_id)
    user = request.user
    
    # Проверка прав: кассир может видеть только свои смены
    if not (user.is_staff or user.is_superuser) and shift.cashier != user:
        return redirect('shifts_list')
    
    receipts = shift.receipts.all()
    
    return render(request, 'core/shift_detail.html', {
        'shift': shift,
        'receipts': receipts
    })


@login_required
def shift_open(request):
    """Открыть смену"""
    user = request.user
    if user.is_staff or user.is_superuser:
        return redirect('dashboard')  # Админ не открывает смены
    
    current_shift = ShiftService.get_current_shift(user)
    if current_shift:
        return redirect('pos')
    
    if request.method == 'POST':
        opening_cash = Decimal(request.POST.get('opening_cash', '0') or '0')
        try:
            shift = ShiftService.open_shift(user, opening_cash)
            return redirect('pos')
        except Exception as e:
            return render(request, 'core/shift_open.html', {'error': str(e)})
    
    return render(request, 'core/shift_open.html')


@login_required
def shift_close(request, shift_id):
    """Закрыть смену"""
    shift = get_object_or_404(Shift, id=shift_id)
    user = request.user
    
    # Проверка прав
    if not (user.is_staff or user.is_superuser) and shift.cashier != user:
        return redirect('shifts_list')
    
    if shift.status == Shift.STATUS_CLOSED:
        return redirect('shift_detail', shift_id=shift_id)
    
    if request.method == 'POST':
        closing_cash = request.POST.get('closing_cash')
        closing_cash = Decimal(closing_cash) if closing_cash else None
        try:
            ShiftService.close_shift(shift, closing_cash)
            return redirect('shift_detail', shift_id=shift_id)
        except Exception as e:
            return render(request, 'core/shift_close.html', {
                'shift': shift,
                'error': str(e)
            })
    
    return render(request, 'core/shift_close.html', {'shift': shift})


@login_required
def products_list(request):
    """Список товаров"""
    is_admin = request.user.is_staff or request.user.is_superuser
    products = Product.objects.all()
    
    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(name__icontains=search) | Q(barcode__icontains=search)
        )
    
    return render(request, 'core/products_list.html', {
        'products': products,
        'is_admin': is_admin,
        'search': search
    })


@login_required
def product_create(request):
    """Создать товар (только админ)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('products_list')
    
    if request.method == 'POST':
        try:
            Product.objects.create(
                name=request.POST.get('name'),
                barcode=request.POST.get('barcode'),
                price=Decimal(request.POST.get('price')),
                stock_qty=int(request.POST.get('stock_qty', 0)),
                is_active=request.POST.get('is_active') == 'on'
            )
            return redirect('products_list')
        except Exception as e:
            return render(request, 'core/product_form.html', {'error': str(e)})
    
    return render(request, 'core/product_form.html')


@login_required
def product_edit(request, product_id):
    """Редактировать товар (только админ)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('products_list')
    
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        try:
            product.name = request.POST.get('name')
            product.barcode = request.POST.get('barcode')
            product.price = Decimal(request.POST.get('price'))
            product.stock_qty = int(request.POST.get('stock_qty', 0))
            product.is_active = request.POST.get('is_active') == 'on'
            product.save()
            return redirect('products_list')
        except Exception as e:
            return render(request, 'core/product_form.html', {
                'product': product,
                'error': str(e)
            })
    
    return render(request, 'core/product_form.html', {'product': product})


@login_required
def reports(request):
    """Отчёты (только админ)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    # Параметры фильтрации
    date_from = request.GET.get('date_from', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().strftime('%Y-%m-%d'))
    cashier_id = request.GET.get('cashier_id')
    
    # Фильтры
    receipts = Receipt.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    )
    
    if cashier_id:
        receipts = receipts.filter(cashier_id=cashier_id)
    
    # Статистика
    sales = receipts.filter(receipt_type=Receipt.RECEIPT_SALE)
    returns = receipts.filter(receipt_type=Receipt.RECEIPT_RETURN)
    
    stats = {
        'total_sales': sales.count(),
        'total_returns': returns.count(),
        'sales_amount': sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00'),
        'returns_amount': returns.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00'),
        'net_amount': (sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')) - 
                     (returns.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')),
        'cash_amount': receipts.filter(payment_method=Receipt.PAYMENT_CASH).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00'),
        'card_amount': receipts.filter(payment_method=Receipt.PAYMENT_CARD).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00'),
    }
    
    # По кассирам
    cashiers_stats = receipts.values('cashier__username').annotate(
        receipts_count=Count('id'),
        total_amount=Sum('total_amount')
    ).order_by('-total_amount')
    
    # По сменам
    shifts = Shift.objects.filter(
        opened_at__date__gte=date_from,
        opened_at__date__lte=date_to
    )
    if cashier_id:
        shifts = shifts.filter(cashier_id=cashier_id)
    
    # Вычисляем статистику по сменам с учётом возвратов
    # Используем shift_total вместо total_amount, чтобы не конфликтовать с property
    shifts_stats = shifts.annotate(
        receipts_count=Count('receipts'),
        # Сумма продаж минус возвраты
        sales_total=Coalesce(
            Sum(
                Case(
                    When(receipts__receipt_type=Receipt.RECEIPT_SALE, then=F('receipts__total_amount')),
                    default=0,
                    output_field=DecimalField()
                )
            ),
            Decimal('0.00')
        ),
        returns_total=Coalesce(
            Sum(
                Case(
                    When(receipts__receipt_type=Receipt.RECEIPT_RETURN, then=F('receipts__total_amount')),
                    default=0,
                    output_field=DecimalField()
                )
            ),
            Decimal('0.00')
        )
    ).annotate(
        shift_total=F('sales_total') - F('returns_total')
    ).order_by('-opened_at')
    
    cashiers = User.objects.filter(is_staff=False, is_superuser=False)
    
    return render(request, 'core/reports.html', {
        'stats': stats,
        'cashiers_stats': cashiers_stats,
        'shifts_stats': shifts_stats,
        'cashiers': cashiers,
        'date_from': date_from,
        'date_to': date_to,
        'cashier_id': cashier_id
    })


@login_required
def cashiers_list(request):
    """Список кассиров (только админ)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    cashiers = User.objects.filter(is_staff=False, is_superuser=False)
    
    return render(request, 'core/cashiers_list.html', {
        'cashiers': cashiers
    })


@login_required
def cashier_detail(request, cashier_id):
    """Детали кассира с его сменами (только админ)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    cashier = get_object_or_404(User, id=cashier_id)
    shifts = Shift.objects.filter(cashier=cashier).order_by('-opened_at')
    
    return render(request, 'core/cashier_detail.html', {
        'cashier': cashier,
        'shifts': shifts
    })


@login_required
def cashier_create(request):
    """Создать кассира (только админ)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            email = request.POST.get('email', '')
            
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                is_staff=False,
                is_superuser=False
            )
            return redirect('cashier_detail', cashier_id=user.id)
        except Exception as e:
            return render(request, 'core/cashier_form.html', {'error': str(e)})
    
    return render(request, 'core/cashier_form.html')


@login_required
def cashier_edit(request, cashier_id):
    """Редактировать кассира (только админ)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    cashier = get_object_or_404(User, id=cashier_id)
    
    if request.method == 'POST':
        try:
            cashier.username = request.POST.get('username')
            cashier.first_name = request.POST.get('first_name', '')
            cashier.last_name = request.POST.get('last_name', '')
            cashier.email = request.POST.get('email', '')
            cashier.is_active = request.POST.get('is_active') == 'on'
            
            password = request.POST.get('password')
            if password:
                cashier.set_password(password)
            
            cashier.save()
            return redirect('cashier_detail', cashier_id=cashier.id)
        except Exception as e:
            return render(request, 'core/cashier_form.html', {
                'cashier': cashier,
                'error': str(e)
            })
    
    return render(request, 'core/cashier_form.html', {'cashier': cashier})
