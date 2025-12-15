from django.contrib import admin
from core.models import Product, Shift, Receipt, ReceiptItem, AuditLog, PaymentSettings


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'barcode', 'price', 'stock_qty', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'barcode']
    list_editable = ['is_active']
    ordering = ['name']


class ReceiptItemInline(admin.TabularInline):
    model = ReceiptItem
    extra = 0
    readonly_fields = ['product', 'qty', 'price_at_moment', 'line_total', 'created_at']
    can_delete = False


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['id', 'shift', 'cashier', 'receipt_type', 'payment_method', 'total_amount', 'created_at']
    list_filter = ['receipt_type', 'payment_method', 'created_at']
    search_fields = ['id', 'cashier__username', 'shift__id']
    readonly_fields = ['created_at']
    inlines = [ReceiptItemInline]
    ordering = ['-created_at']


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['id', 'cashier', 'opened_at', 'closed_at', 'status', 'opening_cash', 'closing_cash']
    list_filter = ['status', 'opened_at', 'cashier']
    search_fields = ['cashier__username', 'id']
    readonly_fields = ['opened_at', 'closed_at']
    ordering = ['-opened_at']


@admin.register(ReceiptItem)
class ReceiptItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'receipt', 'product', 'qty', 'price_at_moment', 'line_total']
    list_filter = ['created_at']
    search_fields = ['product__name', 'receipt__id']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'actor', 'action', 'entity_type', 'entity_id', 'created_at']
    list_filter = ['action', 'entity_type', 'created_at']
    search_fields = ['actor__username', 'action', 'entity_type']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ['updated_at']
    fields = ['qr_code_image', 'card_payment_message']
    
    def has_add_permission(self, request):
        # Разрешаем только одну запись
        return not PaymentSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
