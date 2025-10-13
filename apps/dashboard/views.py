from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
from datetime import datetime, timedelta
from django.utils import timezone
import json
import csv
from io import StringIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from django.contrib.auth.decorators import login_required, user_passes_test
from apps.ventas.views import Venta, VentaDetalle, VentaTipoDePago, TipoPago


@login_required(login_url="/")
@user_passes_test(lambda u: u.groups.filter(name='ADMIN').exists(), login_url='/')
def dashboard_view(request):
    """Vista principal del dashboard"""
    return render(request, 'dashboard/dashboard.html')


def dashboard_data_api(request):
    """API para obtener datos del dashboard"""
    try:
        # Obtener parámetros de la request
        period = request.GET.get('period', 'month')
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')

        # Si no se proporcionan fechas, usar el mes actual
        if not start_date or not end_date:
            today = timezone.now()
            start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            # Convertir fechas a datetime con timezone
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')

            # Hacer timezone-aware usando la zona horaria por defecto de Django
            start_date = timezone.make_aware(start_datetime.replace(hour=0, minute=0, second=0))
            end_date = timezone.make_aware(end_datetime.replace(hour=23, minute=59, second=59, microsecond=999999))

        print("start_date" + str(start_date))
        print("end_date" + str(end_date))
        # Filtrar ventas por rango de fechas usando el timestamp completo
        ventas_queryset = Venta.objects.filter(
            fecha_venta__range=(start_date, end_date)
        )

        # Datos del resumen
        summary_data = ventas_queryset.aggregate(
            total_sales=Sum('total_venta') or 0,
            sales_count=Count('id_venta') or 0,
            total_iva_10=Sum('total_iva_10') or 0,
            total_iva_5=Sum('total_iva_5') or 0
        )

        # Datos de ventas por período
        sales_by_period = get_sales_by_period(ventas_queryset, period)

        # Datos de tipos de pago
        payment_types_data = get_payment_types_data(ventas_queryset)

        return JsonResponse({
            'summary': {
                'totalSales': float(summary_data['total_sales']),
                'salesCount': summary_data['sales_count'],
                'totalIVA10': float(summary_data['total_iva_10']),
                'totalIVA5': float(summary_data['total_iva_5'])
            },
            'salesByPeriod': sales_by_period,
            'paymentTypes': payment_types_data
        })

    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, status=500)


def get_sales_by_period(queryset, period):
    """Obtener ventas agrupadas por período"""
    if period == 'day':
        # Últimos 7 días - usar truncate por día
        data = queryset.annotate(
            day=TruncDate('fecha_venta')
        ).values('day').annotate(
            total=Sum('total_venta')
        ).order_by('day')

        labels = []
        values = []
        # Mapeo de días en español
        day_names = {
            0: 'Lun', 1: 'Mar', 2: 'Mié', 3: 'Jue',
            4: 'Vie', 5: 'Sáb', 6: 'Dom'
        }

        for item in data:
            if item['day']:
                day_name = day_names.get(item['day'].weekday(), 'N/A')
                labels.append(f"{day_name} {item['day'].strftime('%d/%m')}")
                values.append(float(item['total'] or 0))

    elif period == 'week':
        data = queryset.annotate(
            week=TruncWeek('fecha_venta')
        ).values('week').annotate(
            total=Sum('total_venta')
        ).order_by('week')

        labels = []
        values = []
        for i, item in enumerate(data, 1):
            if item['week']:
                labels.append(f'Sem {item["week"].strftime("%W")} ({item["week"].strftime("%d/%m")})')
                values.append(float(item['total'] or 0))

    elif period == 'month':
        data = queryset.annotate(
            month=TruncMonth('fecha_venta')
        ).values('month').annotate(
            total=Sum('total_venta')
        ).order_by('month')

        labels = []
        values = []
        month_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                       'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

        for item in data:
            if item['month']:
                month_num = item['month'].month - 1
                year = item['month'].year
                labels.append(f'{month_names[month_num]} {year}')
                values.append(float(item['total'] or 0))

    elif period == 'year':
        data = queryset.annotate(
            year=TruncYear('fecha_venta')
        ).values('year').annotate(
            total=Sum('total_venta')
        ).order_by('year')

        labels = []
        values = []
        for item in data:
            if item['year']:
                labels.append(str(item['year'].year))
                values.append(float(item['total'] or 0))

    return {
        'labels': labels,
        'data': values
    }


def get_payment_types_data(queryset):
    """Obtener datos de tipos de pago"""
    # Obtener IDs de ventas
    venta_ids = queryset.values_list('id_venta', flat=True)

    # Agrupar por tipo de pago
    payment_data = VentaTipoDePago.objects.filter(
        id_venta__in=venta_ids
    ).select_related('id_tipo_pago').values(
        'id_tipo_pago__descripcion'  # Asumiendo que TipoPago tiene un campo 'nombre'
    ).annotate(
        total=Sum('monto')
    ).order_by('-total')

    labels = []
    data = []
    colors = ['#f60909', '#edda05', '#ff4e02', '#23e404']

    for i, item in enumerate(payment_data):
        labels.append(item['id_tipo_pago__descripcion'] or f'Tipo {i + 1}')
        data.append(float(item['total'] or 0))

    return {
        'labels': labels,
        'data': data,
        'colors': colors[:len(labels)]
    }


def daily_report_view(request):
    """Generar reporte diario en CSV"""
    try:
        # Obtener fecha del reporte
        report_date = request.GET.get('date')
        if report_date:
            report_datetime = datetime.strptime(report_date, '%Y-%m-%d')
            # Crear rango de fecha completa para el día
            start_datetime = timezone.make_aware(report_datetime.replace(hour=0, minute=0, second=0))
            end_datetime = timezone.make_aware(
                report_datetime.replace(hour=23, minute=59, second=59, microsecond=999999))
        else:
            # Usar día actual
            today = timezone.now()
            start_datetime = today.replace(hour=0, minute=0, second=0, microsecond=0)
            end_datetime = today.replace(hour=23, minute=59, second=59, microsecond=999999)
            report_date = today.strftime('%Y-%m-%d')

        # Obtener ventas del día usando el rango de timestamp
        ventas = Venta.objects.filter(
            fecha_venta__gte=start_datetime,
            fecha_venta__lte=end_datetime
        ).select_related('id_cliente').prefetch_related(
            'ventadetalle_set__id_producto',
            'ventatipodepago_set__id_tipo_pago'
        )

        # Crear respuesta CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="reporte_ventas_{report_date}.csv"'

        writer = csv.writer(response)

        # Escribir encabezados
        writer.writerow([
            'ID Venta',
            'Fecha',
            'Cliente',
            'Total Venta',
            'IVA 10%',
            'IVA 5%',
            'Productos',
            'Tipos de Pago'
        ])

        # Escribir datos
        for venta in ventas:
            # Obtener productos
            productos = []
            for detalle in venta.ventadetalle_set.all():
                producto_info = f"{detalle.id_producto.nombre} (Cant: {detalle.cantidad_producto}, Total: ₲{detalle.total_detalle:,.0f})"
                productos.append(producto_info)
            productos_str = ' | '.join(productos)

            # Obtener tipos de pago
            tipos_pago = []
            for pago in venta.ventatipodepago_set.all():
                pago_info = f"{pago.id_tipo_pago.descripcion}: ₲{pago.monto:,.0f}"
                tipos_pago.append(pago_info)
            tipos_pago_str = ' | '.join(tipos_pago)

            writer.writerow([
                venta.id_venta,
                venta.fecha_venta.strftime('%d/%m/%Y %H:%M'),
                str(venta.id_cliente),
                f"₲{venta.total_venta:,.0f}",
                f"₲{venta.total_iva_10:,.0f}",
                f"₲{venta.total_iva_5:,.0f}",
                productos_str,
                tipos_pago_str
            ])

        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def daily_report_pdf_view(request):
    """Generar reporte diario en PDF"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.units import inch

        # Obtener fecha del reporte
        report_date = request.GET.get('date')
        if report_date:
            report_datetime = datetime.strptime(report_date, '%Y-%m-%d')
            # Crear rango de fecha completa para el día
            start_datetime = timezone.make_aware(report_datetime.replace(hour=0, minute=0, second=0))
            end_datetime = timezone.make_aware(
                report_datetime.replace(hour=23, minute=59, second=59, microsecond=999999))
            report_date_str = report_datetime.strftime('%d/%m/%Y')
        else:
            # Usar día actual
            today = timezone.now()
            start_datetime = today.replace(hour=0, minute=0, second=0, microsecond=0)
            end_datetime = today.replace(hour=23, minute=59, second=59, microsecond=999999)
            report_date = today.strftime('%Y-%m-%d')
            report_date_str = today.strftime('%d/%m/%Y')

        # Crear respuesta PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_ventas_{report_date}.pdf"'

        # Crear documento
        doc = SimpleDocTemplate(response, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Título del reporte
        title = Paragraph(
            f"<b>Reporte Diario de Ventas - {report_date_str}</b>",
            styles['Title']
        )
        elements.append(title)
        elements.append(Spacer(1, 20))

        # Obtener ventas del día usando el rango de timestamp
        ventas = Venta.objects.filter(
            fecha_venta__gte=start_datetime,
            fecha_venta__lte=end_datetime
        ).select_related('id_cliente').prefetch_related(
            'ventadetalle_set__id_producto',
            'ventatipodepago_set__id_tipo_pago'
        )

        if not ventas.exists():
            no_data = Paragraph("No se encontraron ventas para esta fecha.", styles['Normal'])
            elements.append(no_data)
        else:
            # Resumen del día
            totals = ventas.aggregate(
                total_ventas=Sum('total_venta'),
                total_iva_10=Sum('total_iva_10'),
                total_iva_5=Sum('total_iva_5'),
                count_ventas=Count('id_venta')
            )

            summary_data = [
                ['Concepto', 'Valor'],
                ['Total de Ventas', f"₲{totals['total_ventas']:,.0f}"],
                ['Cantidad de Ventas', f"{totals['count_ventas']}"],
                ['Total IVA 10%', f"₲{totals['total_iva_10']:,.0f}"],
                ['Total IVA 5%', f"₲{totals['total_iva_5']:,.0f}"]
            ]

            summary_table = Table(summary_data, colWidths=[2 * inch, 2 * inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            elements.append(summary_table)
            elements.append(Spacer(1, 30))

            # Detalle de ventas
            detail_title = Paragraph("<b>Detalle de Ventas</b>", styles['Heading2'])
            elements.append(detail_title)
            elements.append(Spacer(1, 10))

            # Tabla de ventas
            table_data = [['ID', 'Hora', 'Cliente', 'Total', 'IVA 10%', 'IVA 5%']]

            for venta in ventas:
                table_data.append([
                    str(venta.id_venta),
                    venta.fecha_venta.strftime('%H:%M'),
                    str(venta.id_cliente),
                    f"₲{venta.total_venta:,.0f}",
                    f"₲{venta.total_iva_10:,.0f}",
                    f"₲{venta.total_iva_5:,.0f}"
                ])

            detail_table = Table(table_data,
                                 colWidths=[0.8 * inch, 0.8 * inch, 1.5 * inch, 1.2 * inch, 1 * inch, 1 * inch])
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9)
            ]))

            elements.append(detail_table)

        # Generar PDF
        doc.build(elements)
        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def top_products_api(request):
    """API para obtener productos más vendidos"""
    try:
        # Obtener parámetros
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')
        limit = int(request.GET.get('limit', 10))

        if not start_date or not end_date:
            today = timezone.now()
            start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            # Convertir fechas a datetime con timezone
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')

            # Hacer timezone-aware
            start_date = timezone.make_aware(start_datetime.replace(hour=0, minute=0, second=0))
            end_date = timezone.make_aware(end_datetime.replace(hour=23, minute=59, second=59, microsecond=999999))

        # Obtener productos más vendidos
        top_products = VentaDetalle.objects.filter(
            id_venta__fecha_venta__gte=start_date,
            id_venta__fecha_venta__lte=end_date
        ).select_related('id_producto').values(
            'id_producto__nombre'  # Asumiendo que Producto tiene campo 'nombre'
        ).annotate(
            total_cantidad=Sum('cantidad_producto'),
            total_ventas=Sum('total_detalle')
        ).order_by('-total_cantidad')[:limit]

        products_data = []
        for item in top_products:
            products_data.append({
                'nombre': item['id_producto__nombre'],
                'cantidad': float(item['total_cantidad']),
                'ventas': float(item['total_ventas'])
            })

        return JsonResponse({'products': products_data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Vista para obtener estadísticas por cliente
def customer_stats_api(request):
    """API para obtener estadísticas por cliente"""
    try:
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')

        if not start_date or not end_date:
            today = timezone.now()
            start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            # Convertir fechas a datetime con timezone
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')

            # Hacer timezone-aware
            start_date = timezone.make_aware(start_datetime.replace(hour=0, minute=0, second=0))
            end_date = timezone.make_aware(end_datetime.replace(hour=23, minute=59, second=59, microsecond=999999))

        # Obtener estadísticas por cliente
        customer_stats = Venta.objects.filter(
            fecha_venta__gte=start_date,
            fecha_venta__lte=end_date
        ).select_related('id_cliente').values(
            'id_cliente__nombre'  # Asumiendo que Cliente tiene campo 'nombre'
        ).annotate(
            total_compras=Sum('total_venta'),
            cantidad_compras=Count('id_venta')
        ).order_by('-total_compras')[:10]

        customers_data = []
        for item in customer_stats:
            customers_data.append({
                'nombre': item['id_cliente__nombre'],
                'total_compras': float(item['total_compras']),
                'cantidad_compras': item['cantidad_compras']
            })

        return JsonResponse({'customers': customers_data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)