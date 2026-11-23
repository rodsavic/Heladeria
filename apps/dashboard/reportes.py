"""Generacion de reportes descargables (Excel y PDF) de ventas y gastos."""
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date, datetime, time
from io import BytesIO

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.factura.models import Factura, facturas_de_ventas
from apps.gastos.models import Gasto
from apps.ventas.models import Venta

FORMATO_GS = '#,##0'
FORMATO_CANT = '#,##0.##'
SIN_DATO = '-'


def gs(valor):
    """Formatea un monto en guaranies para texto (PDF)."""
    return f"Gs. {round(valor or 0):,.0f}".replace(',', '.')


@dataclass
class DatosReporte:
    desde: date
    hasta: date
    ventas: list = field(default_factory=list)       # una fila por venta
    detalles: list = field(default_factory=list)     # una fila por item vendido
    pagos: list = field(default_factory=list)        # una fila por pago
    gastos: list = field(default_factory=list)       # una fila por gasto
    productos: list = field(default_factory=list)    # ventas agregadas por producto
    por_tipo_pago: list = field(default_factory=list)
    por_tipo_venta: list = field(default_factory=list)
    por_dia: list = field(default_factory=list)
    gastos_por_tipo_pago: list = field(default_factory=list)
    totales: dict = field(default_factory=dict)

    @property
    def es_un_dia(self):
        return self.desde == self.hasta

    @property
    def periodo_texto(self):
        if self.es_un_dia:
            return self.desde.strftime('%d/%m/%Y')
        return f"{self.desde.strftime('%d/%m/%Y')} al {self.hasta.strftime('%d/%m/%Y')}"

    @property
    def sufijo_archivo(self):
        if self.es_un_dia:
            return self.desde.isoformat()
        return f"{self.desde.isoformat()}_a_{self.hasta.isoformat()}"


def _nombre_cliente(cliente):
    nombre = f"{cliente.nombre or ''} {cliente.apellido or ''}".strip()
    return nombre or SIN_DATO


def _nombres_usuarios(ids):
    usuarios = get_user_model().objects.filter(id__in=set(ids))
    return {u.id: (u.get_full_name() or u.username) for u in usuarios}


def _acumular(dic, clave, monto, cantidad=1):
    fila = dic.setdefault(clave, {'monto': 0.0, 'cantidad': 0})
    fila['monto'] += float(monto or 0)
    fila['cantidad'] += cantidad


def _ordenar_por_monto(dic, nombre_clave):
    return [
        {nombre_clave: clave, **valores}
        for clave, valores in sorted(dic.items(), key=lambda kv: kv[1]['monto'], reverse=True)
    ]


def obtener_datos_reporte(desde, hasta):
    """Reune toda la informacion del periodo [desde, hasta] (fechas inclusive)."""
    inicio = timezone.make_aware(datetime.combine(desde, time.min))
    fin = timezone.make_aware(datetime.combine(hasta, time.max))

    ventas = list(
        Venta.objects.filter(fecha_venta__range=(inicio, fin))
        .select_related('id_cliente', 'id_tipo_venta')
        .prefetch_related('ventadetalle_set__id_producto', 'ventatipodepago_set__id_tipo_pago')
        .order_by('fecha_venta', 'id_venta')
    )
    ids_ventas = [v.id_venta for v in ventas]
    facturas = facturas_de_ventas(ids_ventas, [Factura.ESTADO_EMITIDA])
    usuarios = _nombres_usuarios(v.usuario_creacion for v in ventas)

    datos = DatosReporte(desde=desde, hasta=hasta)
    productos, tipos_pago, tipos_venta, dias = {}, {}, {}, OrderedDict()
    total_facturado = 0.0

    for venta in ventas:
        fecha_local = timezone.localtime(venta.fecha_venta)
        cliente = venta.id_cliente
        tipo_venta = venta.id_tipo_venta.nombre if venta.id_tipo_venta else 'Sin tipo'
        factura = facturas.get(venta.id_venta)
        total = float(venta.total_venta or 0)
        if factura:
            total_facturado += total

        pagos_venta = list(venta.ventatipodepago_set.all())
        formas = ', '.join(p.id_tipo_pago.descripcion for p in pagos_venta) or SIN_DATO

        datos.ventas.append({
            'id': venta.id_venta,
            'fecha': fecha_local.replace(tzinfo=None),
            'cliente': _nombre_cliente(cliente),
            'documento': cliente.documento or SIN_DATO,
            'tipo_venta': tipo_venta,
            'cajero': usuarios.get(venta.usuario_creacion, SIN_DATO),
            'formas_pago': formas,
            'items': 0,
            'total': total,
            'iva_10': float(venta.total_iva_10 or 0),
            'iva_5': float(venta.total_iva_5 or 0),
            'factura': factura.nro_factura if factura else '',
        })
        fila_venta = datos.ventas[-1]

        for detalle in venta.ventadetalle_set.all():
            producto = detalle.descripcion_mostrar
            cantidad = float(detalle.cantidad_producto or 0)
            subtotal = float(detalle.total_detalle or 0)
            fila_venta['items'] += cantidad
            datos.detalles.append({
                'id_venta': venta.id_venta,
                'fecha': fila_venta['fecha'],
                'cliente': fila_venta['cliente'],
                'producto': producto,
                'cantidad': cantidad,
                'precio_unitario': subtotal / cantidad if cantidad else 0,
                'subtotal': subtotal,
            })
            _acumular(productos, producto, subtotal, cantidad)

        for pago in pagos_venta:
            descripcion = pago.id_tipo_pago.descripcion
            datos.pagos.append({
                'id_venta': venta.id_venta,
                'fecha': fila_venta['fecha'],
                'cliente': fila_venta['cliente'],
                'tipo_pago': descripcion,
                'monto': float(pago.monto or 0),
            })
            _acumular(tipos_pago, descripcion, pago.monto)

        _acumular(tipos_venta, tipo_venta, total)
        _acumular(dias, fecha_local.date(), total)

    gastos = Gasto.objects.filter(fecha__range=(desde, hasta)).select_related('id_tipo_pago').order_by('fecha', 'id_gasto')
    gastos_por_tipo = {}
    for gasto in gastos:
        tipo = gasto.id_tipo_pago.descripcion if gasto.id_tipo_pago else 'Sin especificar'
        datos.gastos.append({
            'fecha': gasto.fecha,
            'descripcion': gasto.descripcion,
            'tipo_pago': tipo,
            'monto': float(gasto.costo or 0),
        })
        _acumular(gastos_por_tipo, tipo, gasto.costo)

    total_ventas = sum(v['total'] for v in datos.ventas)
    total_gastos = sum(g['monto'] for g in datos.gastos)
    cantidad_ventas = len(datos.ventas)

    datos.productos = [
        {'producto': p['producto'], 'cantidad': p['cantidad'], 'monto': p['monto'],
         'porcentaje': p['monto'] / total_ventas if total_ventas else 0}
        for p in _ordenar_por_monto(productos, 'producto')
    ]
    datos.por_tipo_pago = _ordenar_por_monto(tipos_pago, 'tipo_pago')
    datos.por_tipo_venta = _ordenar_por_monto(tipos_venta, 'tipo_venta')
    datos.gastos_por_tipo_pago = _ordenar_por_monto(gastos_por_tipo, 'tipo_pago')
    datos.por_dia = [{'dia': d, **v} for d, v in dias.items()]
    datos.totales = {
        'cantidad_ventas': cantidad_ventas,
        'total_ventas': total_ventas,
        'ticket_promedio': total_ventas / cantidad_ventas if cantidad_ventas else 0,
        'iva_10': sum(v['iva_10'] for v in datos.ventas),
        'iva_5': sum(v['iva_5'] for v in datos.ventas),
        'items_vendidos': sum(d['cantidad'] for d in datos.detalles),
        'total_facturado': total_facturado,
        'total_sin_facturar': total_ventas - total_facturado,
        'ventas_facturadas': sum(1 for v in datos.ventas if v['factura']),
        'cantidad_gastos': len(datos.gastos),
        'total_gastos': total_gastos,
        'balance': total_ventas - total_gastos,
    }
    return datos


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

def generar_excel(datos):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    relleno_encabezado = PatternFill('solid', fgColor='1F4E78')
    relleno_seccion = PatternFill('solid', fgColor='DDEBF7')
    relleno_total = PatternFill('solid', fgColor='F2F2F2')
    fuente_encabezado = Font(bold=True, color='FFFFFF')
    negrita = Font(bold=True)
    borde_total = Border(top=Side(style='thin'))

    wb = Workbook()

    def hoja_tabla(titulo, columnas, filas, totales=None):
        """columnas: lista de (encabezado, clave, ancho, formato)."""
        ws = wb.create_sheet(titulo)
        for col, (encabezado, _, ancho, _) in enumerate(columnas, 1):
            celda = ws.cell(row=1, column=col, value=encabezado)
            celda.font = fuente_encabezado
            celda.fill = relleno_encabezado
            celda.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            ws.column_dimensions[get_column_letter(col)].width = ancho

        for fila_idx, fila in enumerate(filas, 2):
            for col, (_, clave, _, formato) in enumerate(columnas, 1):
                celda = ws.cell(row=fila_idx, column=col, value=fila.get(clave))
                if formato:
                    celda.number_format = formato

        ultima = len(filas) + 1
        if filas:
            ws.auto_filter.ref = f"A1:{get_column_letter(len(columnas))}{ultima}"
        ws.freeze_panes = 'A2'

        if totales and filas:
            fila_total = ultima + 1
            ws.cell(row=fila_total, column=1, value='TOTAL')
            for col, (_, clave, _, formato) in enumerate(columnas, 1):
                celda = ws.cell(row=fila_total, column=col)
                if clave in totales:
                    letra = get_column_letter(col)
                    celda.value = f"=SUBTOTAL(9,{letra}2:{letra}{ultima})"
                    celda.number_format = formato or FORMATO_GS
                celda.font = negrita
                celda.fill = relleno_total
                celda.border = borde_total
        if not filas:
            ws.cell(row=2, column=1, value='Sin registros en el período.').font = Font(italic=True, color='808080')
        return ws

    # --- Resumen ---------------------------------------------------------
    ws = wb.active
    ws.title = 'Resumen'
    ws.column_dimensions['A'].width = 32
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 14
    ws.column_dimensions['D'].width = 12

    ws['A1'] = 'Reporte de Ventas y Gastos'
    ws['A1'].font = Font(bold=True, size=16)
    ws['A2'] = f"Período: {datos.periodo_texto}"
    ws['A3'] = f"Generado: {timezone.localtime().strftime('%d/%m/%Y %H:%M')}"
    ws['A3'].font = Font(italic=True, color='808080')

    fila = 5

    def seccion(titulo, encabezados):
        nonlocal fila
        ws.cell(row=fila, column=1, value=titulo).font = Font(bold=True, size=12)
        fila += 1
        for col, texto in enumerate(encabezados, 1):
            celda = ws.cell(row=fila, column=col, value=texto)
            celda.font = negrita
            celda.fill = relleno_seccion
        fila += 1

    def linea(valores, formatos, resaltar=False):
        nonlocal fila
        for col, (valor, formato) in enumerate(zip(valores, formatos), 1):
            celda = ws.cell(row=fila, column=col, value=valor)
            if formato:
                celda.number_format = formato
            if resaltar:
                celda.font = negrita
                celda.fill = relleno_total
                celda.border = borde_total
        fila += 1

    t = datos.totales
    seccion('Totales generales', ['Concepto', 'Valor'])
    for concepto, valor, formato, resaltar in [
        ('Total vendido', t['total_ventas'], FORMATO_GS, False),
        ('Cantidad de ventas', t['cantidad_ventas'], '#,##0', False),
        ('Ticket promedio', t['ticket_promedio'], FORMATO_GS, False),
        ('Unidades vendidas', t['items_vendidos'], FORMATO_CANT, False),
        ('IVA 10%', t['iva_10'], FORMATO_GS, False),
        ('IVA 5%', t['iva_5'], FORMATO_GS, False),
        (f"Facturado ({t['ventas_facturadas']} ventas)", t['total_facturado'], FORMATO_GS, False),
        ('Sin facturar', t['total_sin_facturar'], FORMATO_GS, False),
        (f"Total gastos ({t['cantidad_gastos']})", t['total_gastos'], FORMATO_GS, False),
        ('Balance (ventas - gastos)', t['balance'], FORMATO_GS, True),
    ]:
        linea([concepto, valor], [None, formato], resaltar)

    def bloque(titulo, filas, clave, etiqueta_cantidad, total_monto):
        nonlocal fila
        fila += 1
        seccion(titulo, [titulo.split(' por ')[-1].capitalize(), 'Monto', etiqueta_cantidad, '%'])
        if not filas:
            ws.cell(row=fila, column=1, value='Sin registros').font = Font(italic=True, color='808080')
            fila += 1
            return
        for f in filas:
            linea([f[clave], f['monto'], f['cantidad'], f['monto'] / total_monto if total_monto else 0],
                  [None, FORMATO_GS, '#,##0', '0.0%'])
        linea(['Total', sum(f['monto'] for f in filas), sum(f['cantidad'] for f in filas), 1 if total_monto else 0],
              [None, FORMATO_GS, '#,##0', '0.0%'], resaltar=True)

    total_pagos = sum(f['monto'] for f in datos.por_tipo_pago)
    bloque('Ventas por forma de pago', datos.por_tipo_pago, 'tipo_pago', 'Pagos', total_pagos)
    bloque('Ventas por tipo de venta', datos.por_tipo_venta, 'tipo_venta', 'Ventas', t['total_ventas'])
    bloque('Gastos por forma de pago', datos.gastos_por_tipo_pago, 'tipo_pago', 'Gastos', t['total_gastos'])

    if not datos.es_un_dia:
        fila += 1
        seccion('Ventas por día', ['Día', 'Monto', 'Ventas'])
        for f in datos.por_dia:
            linea([f['dia'], f['monto'], f['cantidad']], ['dd/mm/yyyy', FORMATO_GS, '#,##0'])
        linea(['Total', t['total_ventas'], t['cantidad_ventas']], [None, FORMATO_GS, '#,##0'], resaltar=True)

    # --- Hojas de detalle ------------------------------------------------
    hoja_tabla('Ventas', [
        ('N° Venta', 'id', 10, None),
        ('Fecha y hora', 'fecha', 17, 'dd/mm/yyyy hh:mm'),
        ('Cliente', 'cliente', 28, None),
        ('Documento', 'documento', 14, None),
        ('Tipo de venta', 'tipo_venta', 16, None),
        ('Cajero', 'cajero', 18, None),
        ('Formas de pago', 'formas_pago', 24, None),
        ('Unidades', 'items', 10, FORMATO_CANT),
        ('Total', 'total', 14, FORMATO_GS),
        ('IVA 10%', 'iva_10', 12, FORMATO_GS),
        ('IVA 5%', 'iva_5', 12, FORMATO_GS),
        ('N° Factura', 'factura', 18, None),
    ], datos.ventas, totales={'items', 'total', 'iva_10', 'iva_5'})

    hoja_tabla('Productos', [
        ('Producto', 'producto', 36, None),
        ('Cantidad vendida', 'cantidad', 16, FORMATO_CANT),
        ('Total vendido', 'monto', 16, FORMATO_GS),
        ('% del total', 'porcentaje', 12, '0.0%'),
    ], datos.productos, totales={'cantidad', 'monto', 'porcentaje'})

    hoja_tabla('Detalle de ventas', [
        ('N° Venta', 'id_venta', 10, None),
        ('Fecha y hora', 'fecha', 17, 'dd/mm/yyyy hh:mm'),
        ('Cliente', 'cliente', 28, None),
        ('Producto', 'producto', 36, None),
        ('Cantidad', 'cantidad', 10, FORMATO_CANT),
        ('Precio unitario', 'precio_unitario', 15, FORMATO_GS),
        ('Subtotal', 'subtotal', 14, FORMATO_GS),
    ], datos.detalles, totales={'cantidad', 'subtotal'})

    hoja_tabla('Pagos', [
        ('N° Venta', 'id_venta', 10, None),
        ('Fecha y hora', 'fecha', 17, 'dd/mm/yyyy hh:mm'),
        ('Cliente', 'cliente', 28, None),
        ('Forma de pago', 'tipo_pago', 20, None),
        ('Monto', 'monto', 14, FORMATO_GS),
    ], datos.pagos, totales={'monto'})

    hoja_tabla('Gastos', [
        ('Fecha', 'fecha', 12, 'dd/mm/yyyy'),
        ('Descripción', 'descripcion', 40, None),
        ('Forma de pago', 'tipo_pago', 20, None),
        ('Monto', 'monto', 14, FORMATO_GS),
    ], datos.gastos, totales={'monto'})

    salida = BytesIO()
    wb.save(salida)
    return salida.getvalue()


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def generar_pdf(datos):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    salida = BytesIO()
    doc = SimpleDocTemplate(
        salida, pagesize=landscape(A4),
        leftMargin=1.2 * cm, rightMargin=1.2 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm,
        title=f"Reporte {datos.periodo_texto}",
    )
    estilos = getSampleStyleSheet()
    celda = ParagraphStyle('celda', parent=estilos['Normal'], fontSize=8, leading=10)
    h2 = ParagraphStyle('seccion', parent=estilos['Heading2'], keepWithNext=1)
    azul = colors.HexColor('#1F4E78')
    gris_total = colors.HexColor('#F2F2F2')

    def tabla(filas, anchos, alinear_derecha=(), con_total=False):
        filas = [[Paragraph(str(c), celda) if isinstance(c, str) and len(c) > 25 else c for c in f] for f in filas]
        t = Table(filas, colWidths=anchos, repeatRows=1, hAlign='LEFT')
        estilo = [
            ('BACKGROUND', (0, 0), (-1, 0), azul),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7F9FC')]),
            ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#D0D7E1')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]
        for col in alinear_derecha:
            estilo.append(('ALIGN', (col, 0), (col, -1), 'RIGHT'))
        if con_total:
            estilo += [
                ('BACKGROUND', (0, -1), (-1, -1), gris_total),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('LINEABOVE', (0, -1), (-1, -1), 0.8, colors.black),
            ]
        t.setStyle(TableStyle(estilo))
        return t

    def porcentaje(monto, total):
        return f"{(monto / total * 100) if total else 0:.1f}%"

    t = datos.totales
    elementos = [
        Paragraph('Reporte de Ventas y Gastos', estilos['Title']),
        Paragraph(f"Período: <b>{datos.periodo_texto}</b> &nbsp;&nbsp; "
                  f"Generado: {timezone.localtime().strftime('%d/%m/%Y %H:%M')}", estilos['Normal']),
        Spacer(1, 12),
    ]

    # Indicadores principales en una franja
    kpis = [
        ('Total vendido', gs(t['total_ventas'])),
        ('Ventas', str(t['cantidad_ventas'])),
        ('Ticket promedio', gs(t['ticket_promedio'])),
        ('Gastos', gs(t['total_gastos'])),
        ('Balance', gs(t['balance'])),
    ]
    franja = Table([[k for k, _ in kpis], [v for _, v in kpis]], colWidths=[doc.width / len(kpis)] * len(kpis))
    franja.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#5A6B7D')),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 13),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#D0D7E1')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7F9FC')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos += [franja, Spacer(1, 14)]

    # Resumen: impuestos/facturacion + formas de pago + tipo de venta lado a lado
    resumen = tabla([
        ['Concepto', 'Valor'],
        ['IVA 10%', gs(t['iva_10'])],
        ['IVA 5%', gs(t['iva_5'])],
        [f"Facturado ({t['ventas_facturadas']})", gs(t['total_facturado'])],
        ['Sin facturar', gs(t['total_sin_facturar'])],
        ['Unidades vendidas', f"{t['items_vendidos']:,.0f}".replace(',', '.')],
    ], [4 * cm, 3.5 * cm], alinear_derecha=(1,))

    total_pagos = sum(f['monto'] for f in datos.por_tipo_pago)
    pagos = tabla(
        [['Forma de pago', 'Monto', '%']]
        + [[f['tipo_pago'], gs(f['monto']), porcentaje(f['monto'], total_pagos)] for f in datos.por_tipo_pago]
        + [['Total', gs(total_pagos), '100%' if total_pagos else '0%']],
        [3.5 * cm, 3.2 * cm, 1.5 * cm], alinear_derecha=(1, 2), con_total=True,
    )
    tipos = tabla(
        [['Tipo de venta', 'Monto', 'Ventas']]
        + [[f['tipo_venta'], gs(f['monto']), f['cantidad']] for f in datos.por_tipo_venta],
        [3.5 * cm, 3.2 * cm, 1.5 * cm], alinear_derecha=(1, 2),
    )
    lado_a_lado = Table([[resumen, pagos, tipos]], colWidths=[doc.width / 3] * 3)
    lado_a_lado.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    elementos += [lado_a_lado, Spacer(1, 14)]

    if not datos.es_un_dia and datos.por_dia:
        elementos.append(KeepTogether([
            Paragraph('Ventas por día', h2),
            tabla([['Día', 'Ventas', 'Monto']]
                  + [[f['dia'].strftime('%d/%m/%Y'), f['cantidad'], gs(f['monto'])] for f in datos.por_dia]
                  + [['Total', t['cantidad_ventas'], gs(t['total_ventas'])]],
                  [4 * cm, 2.5 * cm, 4 * cm], alinear_derecha=(1, 2), con_total=True),
            Spacer(1, 14),
        ]))

    if datos.productos:
        elementos.append(Paragraph('Productos vendidos', h2))
        elementos.append(tabla(
            [['Producto', 'Cantidad', 'Total', '% del total']]
            + [[p['producto'], f"{p['cantidad']:,.0f}".replace(',', '.'), gs(p['monto']),
                f"{p['porcentaje'] * 100:.1f}%"] for p in datos.productos]
            + [['Total', f"{t['items_vendidos']:,.0f}".replace(',', '.'), gs(t['total_ventas']), '100%']],
            [10 * cm, 3 * cm, 4 * cm, 3 * cm], alinear_derecha=(1, 2, 3), con_total=True,
        ))
        elementos.append(Spacer(1, 14))

    elementos.append(Paragraph('Detalle de ventas', h2))
    if datos.ventas:
        formato_fecha = '%H:%M' if datos.es_un_dia else '%d/%m %H:%M'
        elementos.append(tabla(
            [['N°', 'Hora' if datos.es_un_dia else 'Fecha', 'Cliente', 'Tipo', 'Forma de pago',
              'Total', 'IVA 10%', 'IVA 5%', 'Factura']]
            + [[v['id'], v['fecha'].strftime(formato_fecha), v['cliente'], v['tipo_venta'], v['formas_pago'],
                gs(v['total']), gs(v['iva_10']), gs(v['iva_5']), v['factura'] or SIN_DATO] for v in datos.ventas]
            + [['Total', '', f"{t['cantidad_ventas']} ventas", '', '', gs(t['total_ventas']),
                gs(t['iva_10']), gs(t['iva_5']), '']],
            [1.3 * cm, 2.2 * cm, 5 * cm, 2.8 * cm, 4 * cm, 3 * cm, 2.6 * cm, 2.4 * cm, 3.6 * cm],
            alinear_derecha=(5, 6, 7), con_total=True,
        ))
    else:
        elementos.append(Paragraph('No se registraron ventas en el período.', estilos['Normal']))
    elementos.append(Spacer(1, 14))

    elementos.append(Paragraph('Gastos', h2))
    if datos.gastos:
        elementos.append(tabla(
            [['Fecha', 'Descripción', 'Forma de pago', 'Monto']]
            + [[g['fecha'].strftime('%d/%m/%Y'), g['descripcion'], g['tipo_pago'], gs(g['monto'])]
               for g in datos.gastos]
            + [['Total', '', '', gs(t['total_gastos'])]],
            [2.5 * cm, 12 * cm, 4 * cm, 3.5 * cm], alinear_derecha=(3,), con_total=True,
        ))
    else:
        elementos.append(Paragraph('No se registraron gastos en el período.', estilos['Normal']))

    def pie(canvas, documento):
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(documento.pagesize[0] - documento.rightMargin, 0.6 * cm,
                               f"Página {documento.page}")
        canvas.restoreState()

    doc.build(elementos, onFirstPage=pie, onLaterPages=pie)
    return salida.getvalue()
