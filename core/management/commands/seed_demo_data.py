from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Product
from decimal import Decimal


class Command(BaseCommand):
    help = 'Создаёт демо-данные: админа, кассира и товары'

    def handle(self, *args, **options):
        self.stdout.write('Создание демо-данных...')

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
            self.stdout.write(self.style.SUCCESS(f'✓ Создан администратор: admin / admin12345'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠ Администратор уже существует'))

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
            self.stdout.write(self.style.SUCCESS(f'✓ Создан кассир: cashier1 / cashier12345'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠ Кассир уже существует'))

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

        created_count = 0
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                barcode=product_data['barcode'],
                defaults=product_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Создан товар: {product.name} ({product.barcode})'))
            else:
                # Обновляем данные существующего товара
                for key, value in product_data.items():
                    setattr(product, key, value)
                product.save()

        self.stdout.write(self.style.SUCCESS(f'\n✓ Создано товаров: {created_count}'))
        self.stdout.write(self.style.SUCCESS('\n✓ Демо-данные успешно созданы!'))
        self.stdout.write(self.style.SUCCESS('\nЛогины для входа:'))
        self.stdout.write(self.style.SUCCESS('  Администратор: admin / admin12345'))
        self.stdout.write(self.style.SUCCESS('  Кассир: cashier1 / cashier12345'))


