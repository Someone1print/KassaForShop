from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core import views
from core.api_views import (
    ProductViewSet, ShiftViewSet, product_by_barcode, checkout, receipt_detail
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'shifts', ShiftViewSet, basename='shift')

urlpatterns = [
    # UI Views
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('favicon.ico', views.favicon_view, name='favicon'),
    
    # POS
    path('pos/', views.pos_view, name='pos'),
    
    # Shifts
    path('shifts/', views.shifts_list, name='shifts_list'),
    path('shifts/<int:shift_id>/', views.shift_detail, name='shift_detail'),
    path('shifts/open/', views.shift_open, name='shift_open'),
    path('shifts/<int:shift_id>/close/', views.shift_close, name='shift_close'),
    
    # Products
    path('products/', views.products_list, name='products_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    
    # Cashiers (Admin only)
    path('admin-panel/cashiers/', views.cashiers_list, name='cashiers_list'),
    path('admin-panel/cashiers/<int:cashier_id>/', views.cashier_detail, name='cashier_detail'),
    path('admin-panel/cashiers/create/', views.cashier_create, name='cashier_create'),
    path('admin-panel/cashiers/<int:cashier_id>/edit/', views.cashier_edit, name='cashier_edit'),
]

# API URLs - все под префиксом api/
api_urlpatterns = [
    path('api/products/by-barcode/<str:barcode>/', product_by_barcode, name='product_by_barcode'),
    path('api/pos/checkout/', checkout, name='checkout'),
    path('api/receipts/<int:receipt_id>/', receipt_detail, name='receipt_detail'),
    # Подключаем router URLs с префиксом api/
    path('api/', include(router.urls)),
]

urlpatterns += api_urlpatterns

