from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
from datetime import datetime, timedelta
from django.utils import timezone
import json
import logging
from django.contrib.auth.decorators import login_required, user_passes_test
from apps.ventas.views import Venta, VentaDetalle, VentaTipoDePago, TipoPago
from apps.gastos.models import Gasto
from .reportes import obtener_datos_reporte, generar_excel, generar_pdf

logger = logging.getLogger(__name__)


@login_required(login_url="/")
@user_passes_test(lambda u: u.groups.filter(name='ADMIN').exists(), login_url='/')
def dashboard_view(request):
    """Vista principal del dashboard"""
    return render(request, 'dashboard/dashboard.html')


@login_required(login_url="/")
@user_passes_test(lambda u: u.groups.filter(name='ADMIN').exists(), login_url='/')
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

        # Filtrar ventas por rango de fechas usando el timestamp completo
        ventas_queryset = Venta.objects.filter(
            fecha_venta__range=(start_date, end_date)
        )
        gastos_queryset = Gasto.objects.filter(
            fecha__range=(start_date.date(), end_date.date())
        )

        # Datos del resumen
        summary_data = ventas_queryset.aggregate(
            total_sales=Sum('total_venta') or 0,
            sales_count=Count('id_venta') or 0,
            total_iva_10=Sum('total_iva_10') or 0,
            total_iva_5=Sum('total_iva_5') or 0
        )
        gastos_data = gastos_queryset.aggregate(
            total_expenses=Sum('costo') or 0,
            expenses_count=Count('id_gasto') or 0
        )

        # Datos de ventas por período
        sales_by_period = get_sales_by_period(ventas_queryset, period)
        expenses_by_period = get_expenses_by_period(gastos_queryset, period)

        # Datos de tipos de pago
        payment_types_data = get_payment_types_data(ventas_queryset)

        return JsonResponse({
            'summary': {
                'totalSales': float(summary_data['total_sales']),
                'salesCount': summary_data['sales_count'],
                'totalIVA10': float(summary_data['total_iva_10']),
                'totalIVA5': float(summary_data['total_iva_5']),
                'totalExpenses': float(gastos_data['total_expenses'] or 0),
                'expensesCount': gastos_data['expenses_count'],
                'netBalance': float(summary_data['total_sales']) - float(gastos_data['total_expenses'] or 0)
            },
            'salesByPeriod': sales_by_period,
            'expensesByPeriod': expenses_by_period,
            'paymentTypes': payment_types_data
        })

    except Exception as e:
        logger.exception('Error al obtener datos del dashboard')
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


def get_expenses_by_period(queryset, period):
    """Obtener gastos agrupados por período"""
    if period == 'day':
        data = queryset.annotate(
            day=TruncDate('fecha')
        ).values('day').annotate(
            total=Sum('costo')
        ).order_by('day')

        labels = []
        values = []
        day_names = {
            0: 'Lun', 1: 'Mar', 2: 'Mie', 3: 'Jue',
            4: 'Vie', 5: 'Sab', 6: 'Dom'
        }

        for item in data:
            if item['day']:
                day_name = day_names.get(item['day'].weekday(), 'N/A')
                labels.append(f"{day_name} {item['day'].strftime('%d/%m')}")
                values.append(float(item['total'] or 0))

    elif period == 'week':
        data = queryset.annotate(
            week=TruncWeek('fecha')
        ).values('week').annotate(
            total=Sum('costo')
        ).order_by('week')

        labels = []
        values = []
        for item in data:
            if item['week']:
                labels.append(f'Sem {item["week"].strftime("%W")} ({item["week"].strftime("%d/%m")})')
                values.append(float(item['total'] or 0))

    elif period == 'month':
        data = queryset.annotate(
            month=TruncMonth('fecha')
        ).values('month').annotate(
            total=Sum('costo')
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

    else:
        data = queryset.annotate(
            year=TruncYear('fecha')
        ).values('year').annotate(
            total=Sum('costo')
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


def _periodo_reporte(request):
    """Lee el periodo del reporte: ?start=&end= o ?date= (por defecto, hoy)."""
    hoy = timezone.localdate()
    unico = request.GET.get('date')
    desde = request.GET.get('start') or unico
    hasta = request.GET.get('end') or unico
    desde = datetime.strptime(desde, '%Y-%m-%d').date() if desde else hoy
    hasta = datetime.strptime(hasta, '%Y-%m-%d').date() if hasta else desde
    if hasta < desde:
        desde, hasta = hasta, desde
    return desde, hasta


@login_required(login_url="/")
@user_passes_test(lambda u: u.groups.filter(name='ADMIN').exists(), login_url='/')
def daily_report_view(request):
    """Reporte de ventas y gastos en Excel (una hoja por tipo de informacion)."""
    try:
        desde, hasta = _periodo_reporte(request)
    except ValueError:
        return JsonResponse({'error': 'Fecha inválida, usar formato AAAA-MM-DD.'}, status=400)
    try:
        datos = obtener_datos_reporte(desde, hasta)
        response = HttpResponse(
            generar_excel(datos),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="reporte_ventas_{datos.sufijo_archivo}.xlsx"'
        return response
    except Exception as e:
        logger.exception('Error al generar el reporte Excel')
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url="/")
@user_passes_test(lambda u: u.groups.filter(name='ADMIN').exists(), login_url='/')
def daily_report_pdf_view(request):
    """Reporte de ventas y gastos en PDF."""
    try:
        desde, hasta = _periodo_reporte(request)
    except ValueError:
        return JsonResponse({'error': 'Fecha inválida, usar formato AAAA-MM-DD.'}, status=400)
    try:
        datos = obtener_datos_reporte(desde, hasta)
        response = HttpResponse(generar_pdf(datos), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_ventas_{datos.sufijo_archivo}.pdf"'
        return response
    except Exception as e:
        logger.exception('Error al generar el reporte PDF')
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url="/")
@user_passes_test(lambda u: u.groups.filter(name='ADMIN').exists(), login_url='/')
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
@login_required(login_url="/")
@user_passes_test(lambda u: u.groups.filter(name='ADMIN').exists(), login_url='/')
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
