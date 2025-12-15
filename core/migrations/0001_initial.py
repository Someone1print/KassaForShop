# Generated manually

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Название')),
                ('barcode', models.CharField(max_length=100, unique=True, verbose_name='Штрихкод')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)], verbose_name='Цена')),
                ('stock_qty', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Остаток на складе')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлён')),
            ],
            options={
                'verbose_name': 'Товар',
                'verbose_name_plural': 'Товары',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Shift',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('opened_at', models.DateTimeField(auto_now_add=True, verbose_name='Открыта')),
                ('closed_at', models.DateTimeField(blank=True, null=True, verbose_name='Закрыта')),
                ('status', models.CharField(choices=[('OPEN', 'Открыта'), ('CLOSED', 'Закрыта')], default='OPEN', max_length=10, verbose_name='Статус')),
                ('opening_cash', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='Наличные на начало')),
                ('closing_cash', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Наличные на конец')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлена')),
                ('cashier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shifts', to=settings.AUTH_USER_MODEL, verbose_name='Кассир')),
            ],
            options={
                'verbose_name': 'Смена',
                'verbose_name_plural': 'Смены',
                'ordering': ['-opened_at'],
            },
        ),
        migrations.CreateModel(
            name='Receipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('receipt_type', models.CharField(choices=[('SALE', 'Продажа'), ('RETURN', 'Возврат')], max_length=10, verbose_name='Тип чека')),
                ('payment_method', models.CharField(choices=[('CASH', 'Наличные'), ('CARD', 'Карта')], max_length=10, verbose_name='Способ оплаты')),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)], verbose_name='Сумма')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('cashier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='receipts', to=settings.AUTH_USER_MODEL, verbose_name='Кассир')),
                ('related_sale', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.receipt', verbose_name='Связанная продажа')),
                ('shift', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='receipts', to='core.shift', verbose_name='Смена')),
            ],
            options={
                'verbose_name': 'Чек',
                'verbose_name_plural': 'Чеки',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ReceiptItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qty', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name='Количество')),
                ('price_at_moment', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена на момент продажи')),
                ('line_total', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сумма строки')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.product', verbose_name='Товар')),
                ('receipt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='core.receipt', verbose_name='Чек')),
            ],
            options={
                'verbose_name': 'Позиция чека',
                'verbose_name_plural': 'Позиции чеков',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=100, verbose_name='Действие')),
                ('entity_type', models.CharField(max_length=50, verbose_name='Тип сущности')),
                ('entity_id', models.IntegerField(verbose_name='ID сущности')),
                ('payload', models.JSONField(blank=True, default=dict, verbose_name='Данные')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Запись аудита',
                'verbose_name_plural': 'Журнал аудита',
                'ordering': ['-created_at'],
            },
        ),
    ]
