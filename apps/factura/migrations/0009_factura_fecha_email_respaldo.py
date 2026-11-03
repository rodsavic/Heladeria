from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('factura', '0008_remove_factura_vigencia_timbrado_hasta'),
    ]

    operations = [
        migrations.AddField(
            model_name='factura',
            name='fecha_email_respaldo',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
