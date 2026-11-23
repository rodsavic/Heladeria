"""Lineas de una factura a partir de los detalles de sus ventas.

Una factura agrupada junta muchas ventas del dia: el mismo producto vendido en
varias ventas se informa en una sola linea (cantidades y totales sumados) en
lugar de repetirse una vez por venta.
"""
from dataclasses import dataclass, field

from apps.ventas.models import VentaDetalle


@dataclass
class LineaFactura:
    producto: object
    descripcion: str
    observacion: str
    iva: object                 # IVA propio de la linea (None = el del producto)
    cantidad_producto: float = 0
    total_detalle: float = 0
    ids_venta: list = field(default_factory=list)

    @property
    def descripcion_mostrar(self):
        return self.descripcion or self.producto.nombre

    @property
    def id_venta_id(self):
        return self.ids_venta[0] if self.ids_venta else None


def _clave(detalle):
    if not detalle.cantidad_producto:
        # Sin cantidad no hay precio unitario: la linea queda sola para que
        # quien la use pueda informar el error con su venta.
        return ('sin-cantidad', detalle.pk)
    # El precio unitario forma parte de la clave: SIFEN exige que
    # cantidad x precio unitario coincida con el total de cada item, asi que el
    # mismo producto a distinto precio (ej. salon y PedidosYa) va en otra linea.
    precio_unitario = round(detalle.total_detalle / detalle.cantidad_producto, 2)
    return (
        detalle.id_producto_id,
        precio_unitario,
        detalle.iva,
        detalle.descripcion or '',
        detalle.observacion or '',
    )


def lineas_factura(ventas):
    """Detalles de las ventas agrupados por producto, en orden de aparicion."""
    detalles = (
        VentaDetalle.objects.filter(id_venta__in=ventas)
        .order_by('id_venta__fecha_venta', 'id_venta', 'pk')
        .select_related('id_producto', 'id_producto__id_medida', 'id_producto__id_iva')
    )
    lineas = {}
    for detalle in detalles:
        clave = _clave(detalle)
        linea = lineas.get(clave)
        if linea is None:
            linea = lineas[clave] = LineaFactura(
                producto=detalle.id_producto,
                descripcion=detalle.descripcion or '',
                observacion=detalle.observacion or '',
                iva=detalle.iva,
            )
        linea.cantidad_producto += detalle.cantidad_producto
        linea.total_detalle += detalle.total_detalle
        if detalle.id_venta_id not in linea.ids_venta:
            linea.ids_venta.append(detalle.id_venta_id)
    return list(lineas.values())
