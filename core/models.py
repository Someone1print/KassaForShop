from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class Product(models.Model):
    """Товар"""
    name = models.CharField(max_length=200, verbose_name='Название')
    barcode = models.CharField(max_length=100, unique=True, null=False, blank=False, verbose_name='Штрихкод')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Цена')
    stock_qty = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name='Остаток на складе')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.barcode})"


class Shift(models.Model):
    """Кассовая смена"""
    STATUS_OPEN = 'OPEN'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Открыта'),
        (STATUS_CLOSED, 'Закрыта'),
    ]

    cashier = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shifts', verbose_name='Кассир')
    opened_at = models.DateTimeField(auto_now_add=True, verbose_name='Открыта')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='Закрыта')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN, verbose_name='Статус')
    opening_cash = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Наличные на начало')
    closing_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Наличные на конец')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлена')

    class Meta:
        verbose_name = 'Смена'
        verbose_name_plural = 'Смены'
        ordering = ['-opened_at']

    def __str__(self):
        return f"Смена {self.cashier.username} от {self.opened_at.strftime('%d.%m.%Y %H:%M')}"

    @property
    def total_cash(self):
        """Общая сумма наличных по чекам (продажи минус возвраты)"""
        sales = self.receipts.filter(
            payment_method=Receipt.PAYMENT_CASH,
            receipt_type=Receipt.RECEIPT_SALE
        ).aggregate(total=models.Sum('total_amount'))['total'] or Decimal('0.00')
        returns = self.receipts.filter(
            payment_method=Receipt.PAYMENT_CASH,
            receipt_type=Receipt.RECEIPT_RETURN
        ).aggregate(total=models.Sum('total_amount'))['total'] or Decimal('0.00')
        return sales - returns

    @property
    def total_card(self):
        """Общая сумма по картам по чекам (продажи минус возвраты)"""
        sales = self.receipts.filter(
            payment_method=Receipt.PAYMENT_CARD,
            receipt_type=Receipt.RECEIPT_SALE
        ).aggregate(total=models.Sum('total_amount'))['total'] or Decimal('0.00')
        returns = self.receipts.filter(
            payment_method=Receipt.PAYMENT_CARD,
            receipt_type=Receipt.RECEIPT_RETURN
        ).aggregate(total=models.Sum('total_amount'))['total'] or Decimal('0.00')
        return sales - returns

    @property
    def total_amount(self):
        """Общая сумма всех чеков (продажи минус возвраты)"""
        sales = self.receipts.filter(receipt_type=Receipt.RECEIPT_SALE).aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0.00')
        returns = self.receipts.filter(receipt_type=Receipt.RECEIPT_RETURN).aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0.00')
        return sales - returns


class Receipt(models.Model):
    """Чек (продажа или возврат)"""
    RECEIPT_SALE = 'SALE'
    RECEIPT_RETURN = 'RETURN'
    RECEIPT_TYPE_CHOICES = [
        (RECEIPT_SALE, 'Продажа'),
        (RECEIPT_RETURN, 'Возврат'),
    ]

    PAYMENT_CASH = 'CASH'
    PAYMENT_CARD = 'CARD'
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_CASH, 'Наличные'),
        (PAYMENT_CARD, 'Карта'),
    ]

    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='receipts', verbose_name='Смена')
    cashier = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receipts', verbose_name='Кассир')
    receipt_type = models.CharField(max_length=10, choices=RECEIPT_TYPE_CHOICES, verbose_name='Тип чека')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, verbose_name='Способ оплаты')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Сумма')
    related_sale = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Связанная продажа')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')

    class Meta:
        verbose_name = 'Чек'
        verbose_name_plural = 'Чеки'
        ordering = ['-created_at']

    def __str__(self):
        return f"Чек #{self.id} ({self.get_receipt_type_display()}) - {self.total_amount} руб."


class ReceiptItem(models.Model):
    """Позиция в чеке"""
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='items', verbose_name='Чек')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    qty = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='Количество')
    price_at_moment = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена на момент продажи')
    line_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма строки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')

    class Meta:
        verbose_name = 'Позиция чека'
        verbose_name_plural = 'Позиции чеков'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} x{self.qty} = {self.line_total} руб."


class AuditLog(models.Model):
    """Журнал аудита операций"""
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Пользователь')
    action = models.CharField(max_length=100, verbose_name='Действие')
    entity_type = models.CharField(max_length=50, verbose_name='Тип сущности')
    entity_id = models.IntegerField(verbose_name='ID сущности')
    payload = models.JSONField(default=dict, blank=True, verbose_name='Данные')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        verbose_name = 'Запись аудита'
        verbose_name_plural = 'Журнал аудита'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.entity_type} #{self.entity_id}"


class PaymentSettings(models.Model):
    """Настройки оплаты"""
    qr_code_image = models.ImageField(upload_to='payment_qr/', null=True, blank=True, verbose_name='QR-код для оплаты картой')
    card_payment_message = models.CharField(
        max_length=200, 
        default='Отсканируйте QR-код или приложите карту к терминалу',
        verbose_name='Сообщение при оплате картой'
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Настройки оплаты'
        verbose_name_plural = 'Настройки оплаты'

    def __str__(self):
        return 'Настройки оплаты'
    
    def save(self, *args, **kwargs):
        # Оставляем только одну запись
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Получить настройки (singleton)"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
class UserLoginLog(models.Model):
    """Логирование попыток входа"""
    username = models.CharField(max_length=150, verbose_name='Логин')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP адрес')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время попытки')
    is_success = models.BooleanField(default=False, verbose_name='Результат входа')
    user_agent = models.CharField(max_length=500, null=True, blank=True, verbose_name='Пользовательский агент')

    class Meta:
        verbose_name = 'Попытка входа'
        verbose_name_plural = 'Попытки входа'
        ordering = ['-timestamp']

    def __str__(self):
        result = "Успех" if self.is_success else "Отказ"
        return f"{self.timestamp} - {self.username} ({self.ip_address}): {result}"
