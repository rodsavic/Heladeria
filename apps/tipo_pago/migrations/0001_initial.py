# Generated by Django 3.2.16 on 2025-04-20 21:08

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TipoPago',
            fields=[
                ('id_tipo_pago', models.BigAutoField(primary_key=True, serialize=False)),
                ('descripcion', models.CharField(db_column='descripcion', max_length=50)),
            ],
            options={
                'verbose_name': 'Tipo Pago',
                'verbose_name_plural': 'Tipos de Pago',
                'db_table': 'tipo_pago',
            },
        ),
    ]
