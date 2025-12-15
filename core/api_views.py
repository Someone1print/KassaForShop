from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from core.models import Product, Shift, Receipt
from core.serializers import (
    ProductSerializer, ShiftSerializer, ReceiptSerializer, 
    UserSerializer, CheckoutSerializer
)
from core.services.sales_service import SalesService
from core.services.shift_service import ShiftService


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """API для товаров"""
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) | 
                models.Q(barcode__icontains=search)
            )
        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_by_barcode(request, barcode):
    """Получить товар по штрихкоду"""
    try:
        product = Product.objects.get(barcode=barcode, is_active=True)
        serializer = ProductSerializer(product)
        return Response(serializer.data)
    except Product.DoesNotExist:
        return Response(
            {'error': 'Товар не найден'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def receipt_detail(request, receipt_id):
    """Получить детали чека"""
    try:
        receipt = Receipt.objects.prefetch_related('items__product').get(id=receipt_id)
        # Проверка прав: кассир может видеть только свои чеки
        if not (request.user.is_staff or request.user.is_superuser) and receipt.cashier != request.user:
            return Response(
                {'error': 'У вас нет прав на просмотр этого чека'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = ReceiptSerializer(receipt)
        return Response(serializer.data)
    except Receipt.DoesNotExist:
        return Response(
            {'error': 'Чек не найден'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkout(request):
    """Оформить покупку или возврат"""
    serializer = CheckoutSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    receipt_type = data['receipt_type']
    payment_method = data['payment_method']
    items = data['items']
    related_sale_id = data.get('related_sale_id')
    
    # Получаем текущую смену кассира
    shift = ShiftService.get_current_shift(request.user)
    if not shift:
        return Response(
            {'error': 'У вас нет открытой смены. Откройте смену перед оформлением покупки.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        if receipt_type == Receipt.RECEIPT_SALE:
            receipt = SalesService.create_sale(shift, request.user, payment_method, items)
        else:
            receipt = SalesService.create_return(shift, request.user, payment_method, items, related_sale_id)
        
        receipt_serializer = ReceiptSerializer(receipt)
        return Response({
            'receipt': receipt_serializer.data,
            'message': 'Покупка успешно оформлена'
        }, status=status.HTTP_201_CREATED)
    
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


class ShiftViewSet(viewsets.ReadOnlyModelViewSet):
    """API для смен"""
    serializer_class = ShiftSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            # Админ видит все смены
            return Shift.objects.all()
        else:
            # Кассир видит только свои смены
            return Shift.objects.filter(cashier=user)
    
    @action(detail=False, methods=['post'])
    def open(self, request):
        """Открыть смену"""
        opening_cash = request.data.get('opening_cash', 0)
        
        try:
            shift = ShiftService.open_shift(request.user, opening_cash)
            serializer = ShiftSerializer(shift)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Закрыть смену"""
        shift = get_object_or_404(Shift, pk=pk)
        
        # Проверка прав: кассир может закрыть только свою смену, админ - любую
        if not (request.user.is_staff or request.user.is_superuser) and shift.cashier != request.user:
            return Response(
                {'error': 'У вас нет прав на закрытие этой смены'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        closing_cash = request.data.get('closing_cash')
        
        try:
            shift = ShiftService.close_shift(shift, closing_cash)
            serializer = ShiftSerializer(shift)
            return Response(serializer.data)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

