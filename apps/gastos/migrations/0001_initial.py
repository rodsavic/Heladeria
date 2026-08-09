from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Gasto",
            fields=[
                ("id_gasto", models.AutoField(primary_key=True, serialize=False)),
                ("descripcion", models.CharField(db_column="descripcion", max_length=255)),
                ("costo", models.DecimalField(db_column="costo", decimal_places=2, max_digits=12)),
                ("fecha", models.DateField(db_column="fecha")),
                ("usuario_creacion", models.IntegerField(blank=True, db_column="usuario_creacion", null=True)),
                ("usuario_modificacion", models.IntegerField(blank=True, db_column="usuario_modificacion", null=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")),
                ("fecha_modificacion", models.DateTimeField(blank=True, db_column="fecha_modificacion", null=True)),
            ],
            options={
                "verbose_name": "Gasto",
                "verbose_name_plural": "Gastos",
                "db_table": "gastos",
            },
        ),
    ]
