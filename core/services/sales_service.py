from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from core.models import Product, Shift, Receipt, ReceiptItem, AuditLog


class SalesService:
    """Сервис для операций продажи и возврата"""

    @staticmethod
    @transaction.atomic
    def create_sale(shift: Shift, cashier, payment_method: str, items: list) -> Receipt:
        """
        Создать продажу
        
        Args:
            shift: Открытая смена
            cashier: Кассир
            payment_method: CASH или CARD
            items: Список словарей {'product_id': int, 'qty': int}
        
        Returns:
            Созданный чек
        """
        if shift.status != Shift.STATUS_OPEN:
            raise ValidationError("Смена должна быть открыта для создания продажи")
        
        if shift.cashier != cashier:
            raise ValidationError("Кассир может работать только со своей сменой")

        receipt = Receipt.objects.create(
            shift=shift,
            cashier=cashier,
            receipt_type=Receipt.RECEIPT_SALE,
            payment_method=payment_method,
            total_amount=Decimal('0.00')
        )

        total = Decimal('0.00')
        
        for item_data in items:
            product_id = item_data['product_id']
            qty = item_data['qty']
            
            try:
                product = Product.objects.get(id=product_id, is_active=True)
            except Product.DoesNotExist:
                raise ValidationError(f"Товар с ID {product_id} не найден или неактивен")
            
            if product.stock_qty < qty:
                raise ValidationError(f"Недостаточно товара {product.name} на складе. Доступно: {product.stock_qty}, требуется: {qty}")
            
            price_at_moment = product.price
            line_total = price_at_moment * qty
            
            ReceiptItem.objects.create(
                receipt=receipt,
                product=product,
                qty=qty,
                price_at_moment=price_at_moment,
                line_total=line_total
            )
            
            # Уменьшаем остаток
            product.stock_qty -= qty
            product.save()
            
            total += line_total
        
        receipt.total_amount = total
        receipt.save()
        
        # Аудит
        AuditLog.objects.create(
            actor=cashier,
            action='SALE_CREATED',
            entity_type='Receipt',
            entity_id=receipt.id,
            payload={
                'shift_id': shift.id,
                'payment_method': payment_method,
                'total': str(total),
                'items_count': len(items)
            }
        )
        
        return receipt

    @staticmethod
    @transaction.atomic
    def create_return(shift: Shift, cashier, payment_method: str, items: list, related_sale_id=None) -> Receipt:
        """
        Создать возврат
        
        Args:
            shift: Открытая смена
            cashier: Кассир
            payment_method: CASH или CARD
            items: Список словарей {'product_id': int, 'qty': int}
            related_sale_id: ID исходной продажи (опционально)
        
        Returns:
            Созданный чек возврата
        """
        if shift.status != Shift.STATUS_OPEN:
            raise ValidationError("Смена должна быть открыта для создания возврата")
        
        if shift.cashier != cashier:
            raise ValidationError("Кассир может работать только со своей сменой")

        related_sale = None
        if related_sale_id:
            try:
                related_sale = Receipt.objects.get(id=related_sale_id, receipt_type=Receipt.RECEIPT_SALE)
            except Receipt.DoesNotExist:
                pass  # Не критично, если исходный чек не найден

        receipt = Receipt.objects.create(
            shift=shift,
            cashier=cashier,
            receipt_type=Receipt.RECEIPT_RETURN,
            payment_method=payment_method,
            total_amount=Decimal('0.00'),
            related_sale=related_sale
        )

        total = Decimal('0.00')
        
        for item_data in items:
            product_id = item_data['product_id']
            qty = item_data['qty']
            
            try:
                product = Product.objects.get(id=product_id, is_active=True)
            except Product.DoesNotExist:
                raise ValidationError(f"Товар с ID {product_id} не найден или неактивен")
            
            price_at_moment = product.price
            line_total = price_at_moment * qty
            
            ReceiptItem.objects.create(
                receipt=receipt,
                product=product,
                qty=qty,
                price_at_moment=price_at_moment,
                line_total=line_total
            )
            
            # Увеличиваем остаток
            product.stock_qty += qty
            product.save()
            
            total += line_total
        
        receipt.total_amount = total
        receipt.save()
        
        # Аудит
        AuditLog.objects.create(
            actor=cashier,
            action='RETURN_CREATED',
            entity_type='Receipt',
            entity_id=receipt.id,
            payload={
                'shift_id': shift.id,
                'payment_method': payment_method,
                'total': str(total),
                'items_count': len(items),
                'related_sale_id': related_sale_id
            }
        )
        
        return receipt

