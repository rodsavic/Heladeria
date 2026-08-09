import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tipo_pago", "0001_initial"),
        ("gastos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="gasto",
            name="id_tipo_pago",
            field=models.ForeignKey(
                blank=True,
                null=True,
                db_column="id_tipo_pago",
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="tipo_pago.tipopago",
            ),
        ),
    ]
