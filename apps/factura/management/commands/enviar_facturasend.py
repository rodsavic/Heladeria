"""Envia a FacturaSend las facturas que quedaron pendientes.

Pensado para correr en una tarea programada (cron / Programador de tareas
de Windows) cuando la empresa trabaja en modo asincrono
(ConfiguracionEmpresa.facturasend_sincrono = False): la factura se emite
localmente al instante y este comando se encarga de enviarla a FacturaSend
poco despues, sin bloquear al usuario que esta facturando.

Uso:
    python manage.py enviar_facturasend
"""
from django.core.management.base import BaseCommand

from apps.configuracion.models import ConfiguracionEmpresa
from apps.factura.facturasend_service import enviar_documento
from apps.factura.models import Factura


class Command(BaseCommand):
    help = 'Envia a FacturaSend las facturas emitidas que todavia no tienen CDC.'

    def handle(self, *args, **options):
        configuracion = ConfiguracionEmpresa.objects.first()
        if not configuracion or not configuracion.facturasend_url or not configuracion.facturasend_api_key:
            self.stderr.write('Configuracion de FacturaSend incompleta (URL o API Key vacia).')
            return

        pendientes = Factura.objects.filter(
            estado=Factura.ESTADO_EMITIDA,
            cdc='',
        ).exclude(estado_sifen=Factura.ESTADO_SIFEN_CANCELADO)

        total = pendientes.count()
        if total == 0:
            self.stdout.write('No hay facturas pendientes de envio.')
            return

        enviadas, fallidas = 0, 0
        for factura in pendientes:
            ok, mensaje = enviar_documento(factura, configuracion)
            if ok:
                enviadas += 1
                self.stdout.write(self.style.SUCCESS(f'{factura.nro_factura}: {mensaje}'))
            else:
                fallidas += 1
                self.stdout.write(self.style.WARNING(f'{factura.nro_factura}: {mensaje}'))

        self.stdout.write(self.style.SUCCESS(f'Procesadas {total}: {enviadas} enviadas, {fallidas} con error.'))
