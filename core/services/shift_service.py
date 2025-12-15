from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models import Shift, AuditLog


class ShiftService:
    """Сервис для управления сменами"""

    @staticmethod
    @transaction.atomic
    def open_shift(cashier, opening_cash: Decimal = None) -> Shift:
        """
        Открыть смену для кассира
        
        Args:
            cashier: Кассир
            opening_cash: Наличные на начало смены
        
        Returns:
            Созданная смена
        """
        # Проверяем, нет ли уже открытой смены
        existing_open_shift = Shift.objects.filter(
            cashier=cashier,
            status=Shift.STATUS_OPEN
        ).first()
        
        if existing_open_shift:
            raise ValidationError("У кассира уже есть открытая смена")
        
        shift = Shift.objects.create(
            cashier=cashier,
            status=Shift.STATUS_OPEN,
            opening_cash=opening_cash or Decimal('0.00')
        )
        
        # Аудит
        AuditLog.objects.create(
            actor=cashier,
            action='SHIFT_OPENED',
            entity_type='Shift',
            entity_id=shift.id,
            payload={
                'opening_cash': str(opening_cash or Decimal('0.00'))
            }
        )
        
        return shift

    @staticmethod
    @transaction.atomic
    def close_shift(shift: Shift, closing_cash: Decimal = None) -> Shift:
        """
        Закрыть смену
        
        Args:
            shift: Смена для закрытия
            closing_cash: Наличные на конец смены
        
        Returns:
            Закрытая смена
        """
        if shift.status == Shift.STATUS_CLOSED:
            raise ValidationError("Смена уже закрыта")
        
        shift.status = Shift.STATUS_CLOSED
        shift.closed_at = timezone.now()
        if closing_cash is not None:
            shift.closing_cash = closing_cash
        shift.save()
        
        # Аудит
        AuditLog.objects.create(
            actor=shift.cashier,
            action='SHIFT_CLOSED',
            entity_type='Shift',
            entity_id=shift.id,
            payload={
                'closing_cash': str(closing_cash) if closing_cash else None,
                'total_amount': str(shift.total_amount),
                'total_cash': str(shift.total_cash),
                'total_card': str(shift.total_card)
            }
        )
        
        return shift

    @staticmethod
    def get_current_shift(cashier):
        """Получить текущую открытую смену кассира"""
        return Shift.objects.filter(
            cashier=cashier,
            status=Shift.STATUS_OPEN
        ).first()

