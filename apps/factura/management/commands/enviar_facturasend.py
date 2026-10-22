"""Envia a FacturaSend las facturas que quedaron pendientes y actualiza el
estado SIFEN de las que siguen esperando respuesta.

Pensado para correr en una tarea programada (cron / Programador de tareas
de Windows), por ejemplo cada 10 minutos como recomienda FacturaSend:

1. Envia las facturas emitidas que todavia no tienen CDC (modo asincrono,
   ConfiguracionEmpresa.facturasend_sincrono = False, o envios que fallaron).
2. Consulta el estado (POST /de/estado) de las facturas en 0-Generado o
   1-Enviado en lote, ya que /lote/create no devuelve la aprobacion de SIFEN.
3. Revisa el envio de correo (KuDE) de las facturas aprobadas en los
   ultimos 7 dias y reenvia una vez las que fallaron.

Las facturas rechazadas no se reenvian solas (fallarian con el mismo error):
se corrige el dato y se reenvian desde el detalle de la factura.

Uso:
    python manage.py enviar_facturasend
"""
from django.core.management.base import BaseCommand

from apps.configuracion.models import ConfiguracionEmpresa
from apps.factura.facturasend_service import actualizar_estados, enviar_documento, verificar_envios_email
from apps.factura.models import Factura


class Command(BaseCommand):
    help = 'Envia a FacturaSend las facturas sin CDC y actualiza el estado SIFEN de las pendientes.'

    def handle(self, *args, **options):
        configuracion = ConfiguracionEmpresa.objects.first()
        if not configuracion or not configuracion.facturasend_url or not configuracion.facturasend_api_key:
            self.stderr.write('Configuracion de FacturaSend incompleta (URL o API Key vacia).')
            return

        self._enviar_pendientes(configuracion)
        self._actualizar_estados(configuracion)
        self._verificar_correos(configuracion)

    def _enviar_pendientes(self, configuracion):
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

    def _actualizar_estados(self, configuracion):
        actualizadas, error = actualizar_estados(configuracion)
        if error:
            self.stdout.write(self.style.WARNING(f'Error al consultar estados en FacturaSend: {error}'))
        self.stdout.write(self.style.SUCCESS(f'Estados SIFEN actualizados: {actualizadas}.'))

    def _verificar_correos(self, configuracion):
        verificadas, reenviadas, error = verificar_envios_email(configuracion)
        if error:
            self.stdout.write(self.style.WARNING(f'Error al consultar envios de correo: {error}'))
        self.stdout.write(self.style.SUCCESS(
            f'Correos verificados: {verificadas}, reenviados por fallo: {reenviadas}.'
        ))
