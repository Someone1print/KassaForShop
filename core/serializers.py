from rest_framework import serializers
from django.contrib.auth.models import User
from core.models import Product, Shift, Receipt, ReceiptItem


class ProductSerializer(serializers.ModelSerializer):
    """Сериализатор товара"""
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'barcode', 'price', 'stock_qty', 'is_active']


class ReceiptItemSerializer(serializers.ModelSerializer):
    """Сериализатор позиции чека"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = ReceiptItem
        fields = ['id', 'product', 'product_name', 'qty', 'price_at_moment', 'line_total']


class ReceiptSerializer(serializers.ModelSerializer):
    """Сериализатор чека"""
    items = ReceiptItemSerializer(many=True, read_only=True)
    cashier_username = serializers.CharField(source='cashier.username', read_only=True)
    
    class Meta:
        model = Receipt
        fields = ['id', 'shift', 'cashier', 'cashier_username', 'receipt_type', 'payment_method', 
                  'total_amount', 'created_at', 'items']


class ShiftSerializer(serializers.ModelSerializer):
    """Сериализатор смены"""
    cashier_username = serializers.CharField(source='cashier.username', read_only=True)
    total_cash = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_card = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    receipts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Shift
        fields = ['id', 'cashier', 'cashier_username', 'opened_at', 'closed_at', 'status',
                  'opening_cash', 'closing_cash', 'total_cash', 'total_card', 'total_amount',
                  'receipts_count']
    
    def get_receipts_count(self, obj):
        return obj.receipts.count()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя"""
    is_admin = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_admin']
    
    def get_is_admin(self, obj):
        return obj.is_staff or obj.is_superuser


class CheckoutSerializer(serializers.Serializer):
    """Сериализатор для оформления покупки"""
    receipt_type = serializers.ChoiceField(choices=[Receipt.RECEIPT_SALE, Receipt.RECEIPT_RETURN])
    payment_method = serializers.ChoiceField(choices=[Receipt.PAYMENT_CASH, Receipt.PAYMENT_CARD])
    items = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField()
        )
    )
    related_sale_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_items(self, value):
        """Валидация списка товаров"""
        if not value:
            raise serializers.ValidationError("Список товаров не может быть пустым")
        
        for item in value:
            if 'product_id' not in item or 'qty' not in item:
                raise serializers.ValidationError("Каждый товар должен содержать product_id и qty")
            if item['qty'] <= 0:
                raise serializers.ValidationError("Количество должно быть больше 0")
        
        return value


