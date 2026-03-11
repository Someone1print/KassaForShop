# Generated manually - Data migration with demo data

from django.db import migrations
from django.contrib.auth.models import User
from decimal import Decimal


def create_demo_data(apps, schema_editor):
    """Создание демо-данных: админа, кассира и товаров"""
    # Получаем модели из миграции
    Product = apps.get_model('core', 'Product')
    
    # Создание администратора
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'is_staff': True,
            'is_superuser': True,
            'first_name': 'Администратор',
        }
    )
    if created:
        admin_user.set_password('admin12345')
        admin_user.save()
    
    # Создание кассира
    cashier_user, created = User.objects.get_or_create(
        username='cashier1',
        defaults={
            'email': 'cashier1@example.com',
            'is_staff': False,
            'is_superuser': False,
            'first_name': 'Кассир',
            'last_name': 'Первый',
        }
    )
    if created:
        cashier_user.set_password('cashier12345')
        cashier_user.save()
    
    # Создание товаров
    products_data = [
        {'name': 'Хлеб белый', 'barcode': '4601234567890', 'price': Decimal('45.00'), 'stock_qty': 50},
        {'name': 'Молоко 1л', 'barcode': '4601234567891', 'price': Decimal('85.50'), 'stock_qty': 30},
        {'name': 'Яйца куриные 10шт', 'barcode': '4601234567892', 'price': Decimal('120.00'), 'stock_qty': 25},
        {'name': 'Сахар 1кг', 'barcode': '4601234567893', 'price': Decimal('65.00'), 'stock_qty': 40},
        {'name': 'Масло сливочное 200г', 'barcode': '4601234567894', 'price': Decimal('150.00'), 'stock_qty': 20},
        {'name': 'Сыр твёрдый 300г', 'barcode': '4601234567895', 'price': Decimal('280.00'), 'stock_qty': 15},
        {'name': 'Колбаса варёная 300г', 'barcode': '4601234567896', 'price': Decimal('320.00'), 'stock_qty': 18},
        {'name': 'Макароны 500г', 'barcode': '4601234567897', 'price': Decimal('75.00'), 'stock_qty': 35},
        {'name': 'Рис 1кг', 'barcode': '4601234567898', 'price': Decimal('95.00'), 'stock_qty': 28},
        {'name': 'Мука пшеничная 1кг', 'barcode': '4601234567899', 'price': Decimal('55.00'), 'stock_qty': 45},
    ]
    
    for product_data in products_data:
        Product.objects.get_or_create(
            barcode=product_data['barcode'],
            defaults=product_data
        )


def remove_demo_data(apps, schema_editor):
    """Удаление демо-данных (для отката миграции)"""
    User = apps.get_model('auth', 'User')
    Product = apps.get_model('core', 'Product')
    
    # Удаляем пользователей
    User.objects.filter(username__in=['admin', 'cashier1']).delete()
    
    # Удаляем товары
    Product.objects.filter(barcode__startswith='460123456789').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_demo_data, remove_demo_data),
    ]


