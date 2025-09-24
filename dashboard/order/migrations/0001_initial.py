import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('book', '0003_alter_author_options_author_contact_number_and_more'),

    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('address', models.CharField(max_length=255, verbose_name='adress')),
                ('contact_number', models.CharField(max_length=20, verbose_name='phone_num')),
            ],
            options={
                'verbose_name': 'customer',
                'verbose_name_plural': 'customer_list',
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_date', models.DateTimeField(auto_now_add=True, verbose_name='order_date')),
                ('delivery_date', models.DateTimeField(blank=True, null=True, verbose_name='delivery_date')),
                ('order_source', models.CharField(max_length=50, verbose_name='order_source')),
                ('delivery_method', models.CharField(max_length=50, verbose_name='delivery_method')),
                ('requests', models.TextField(blank=True, verbose_name='requests')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='order.customer', verbose_name='customer')),
            ],
            options={
                'verbose_name': 'order_ID',
                'verbose_name_plural': 'order_list',
                'ordering': ['-order_date'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(verbose_name='quantity')),
                ('discount_rate', models.DecimalField(decimal_places=2, default=0.0, max_digits=5, verbose_name='discount_rate')),
                ('additional_item', models.CharField(blank=True, max_length=100, verbose_name='additional_item')),
                ('additional_price', models.IntegerField(verbose_name='additional_price')),
                ('total_price', models.IntegerField(verbose_name='supply_price')),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_items', to='book.book', verbose_name='book_ID')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_items', to='order.order', verbose_name='order_ID')),
            ],
            options={
                'verbose_name': 'order_product',
                'verbose_name_plural': 'order_product_list',
            },
        ),
    ]
