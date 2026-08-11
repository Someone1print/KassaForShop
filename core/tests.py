"""Тесты сервисного слоя кассы: смены, продажи, возвраты.

Ключевые инварианты: остатки на складе, атомарность продажи,
права кассира на смену, аудит операций.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import AuditLog, Product, Receipt, Shift
from core.services.sales_service import SalesService
from core.services.shift_service import ShiftService


class BaseKassaTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cashier = User.objects.create_user(username='cashier', password='StrongPass123')
        cls.other_cashier = User.objects.create_user(username='other', password='StrongPass123')

    def open_shift(self, cashier=None):
        return ShiftService.open_shift(cashier or self.cashier, Decimal('1000.00'))

    def make_product(self, name='Хлеб', barcode='4600000000001', price='45.00', stock=10):
        return Product.objects.create(
            name=name, barcode=barcode, price=Decimal(price), stock_qty=stock,
        )


class ShiftServiceTests(BaseKassaTestCase):
    def test_open_shift_creates_open_shift_with_audit(self):
        shift = self.open_shift()
        self.assertEqual(shift.status, Shift.STATUS_OPEN)
        self.assertEqual(shift.opening_cash, Decimal('1000.00'))
        self.assertTrue(
            AuditLog.objects.filter(action='SHIFT_OPENED', entity_id=shift.id).exists()
        )

    def test_second_open_shift_for_same_cashier_forbidden(self):
        self.open_shift()
        with self.assertRaises(ValidationError):
            self.open_shift()

    def test_close_shift(self):
        shift = self.open_shift()
        closed = ShiftService.close_shift(shift, Decimal('1500.00'))
        self.assertEqual(closed.status, Shift.STATUS_CLOSED)
        self.assertIsNotNone(closed.closed_at)
        self.assertEqual(closed.closing_cash, Decimal('1500.00'))

    def test_close_already_closed_shift_forbidden(self):
        shift = self.open_shift()
        ShiftService.close_shift(shift)
        with self.assertRaises(ValidationError):
            ShiftService.close_shift(shift)

    def test_get_current_shift(self):
        self.assertIsNone(ShiftService.get_current_shift(self.cashier))
        shift = self.open_shift()
        self.assertEqual(ShiftService.get_current_shift(self.cashier), shift)


class SalesServiceTests(BaseKassaTestCase):
    def test_create_sale_decrements_stock_and_totals(self):
        shift = self.open_shift()
        bread = self.make_product('Хлеб', '4600000000001', '45.00', stock=10)
        milk = self.make_product('Молоко', '4600000000002', '80.50', stock=5)

        receipt = SalesService.create_sale(
            shift, self.cashier, Receipt.PAYMENT_CASH,
            [
                {'product_id': bread.id, 'qty': 2},
                {'product_id': milk.id, 'qty': 3},
            ],
        )

        bread.refresh_from_db()
        milk.refresh_from_db()
        self.assertEqual(bread.stock_qty, 8)
        self.assertEqual(milk.stock_qty, 2)
        self.assertEqual(receipt.total_amount, Decimal('331.50'))
        self.assertEqual(receipt.items.count(), 2)
        self.assertTrue(
            AuditLog.objects.filter(action='SALE_CREATED', entity_id=receipt.id).exists()
        )

    def test_sale_with_insufficient_stock_rolls_back_atomically(self):
        shift = self.open_shift()
        bread = self.make_product('Хлеб', '4600000000001', '45.00', stock=10)
        milk = self.make_product('Молоко', '4600000000002', '80.50', stock=1)

        with self.assertRaises(ValidationError):
            SalesService.create_sale(
                shift, self.cashier, Receipt.PAYMENT_CASH,
                [
                    {'product_id': bread.id, 'qty': 2},   # хватает
                    {'product_id': milk.id, 'qty': 5},    # не хватает
                ],
            )

        # Транзакция откатилась целиком: остаток хлеба не изменился, чека нет.
        bread.refresh_from_db()
        self.assertEqual(bread.stock_qty, 10)
        self.assertEqual(Receipt.objects.count(), 0)

    def test_sale_requires_open_shift(self):
        shift = self.open_shift()
        ShiftService.close_shift(shift)
        product = self.make_product()
        with self.assertRaises(ValidationError):
            SalesService.create_sale(
                shift, self.cashier, Receipt.PAYMENT_CASH,
                [{'product_id': product.id, 'qty': 1}],
            )

    def test_cashier_cannot_sell_on_foreign_shift(self):
        shift = self.open_shift()
        product = self.make_product()
        with self.assertRaises(ValidationError):
            SalesService.create_sale(
                shift, self.other_cashier, Receipt.PAYMENT_CASH,
                [{'product_id': product.id, 'qty': 1}],
            )

    def test_inactive_product_cannot_be_sold(self):
        shift = self.open_shift()
        product = self.make_product()
        product.is_active = False
        product.save()
        with self.assertRaises(ValidationError):
            SalesService.create_sale(
                shift, self.cashier, Receipt.PAYMENT_CASH,
                [{'product_id': product.id, 'qty': 1}],
            )

    def test_return_restores_stock_and_links_sale(self):
        shift = self.open_shift()
        product = self.make_product(stock=10)
        sale = SalesService.create_sale(
            shift, self.cashier, Receipt.PAYMENT_CARD,
            [{'product_id': product.id, 'qty': 4}],
        )

        refund = SalesService.create_return(
            shift, self.cashier, Receipt.PAYMENT_CARD,
            [{'product_id': product.id, 'qty': 4}],
            related_sale_id=sale.id,
        )

        product.refresh_from_db()
        self.assertEqual(product.stock_qty, 10)
        self.assertEqual(refund.receipt_type, Receipt.RECEIPT_RETURN)
        self.assertEqual(refund.related_sale, sale)
        self.assertTrue(
            AuditLog.objects.filter(action='RETURN_CREATED', entity_id=refund.id).exists()
        )
