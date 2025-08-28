from django.urls import path
from .views import *

app_name = 'dashboard'
urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    # APIs para datos del dashboard
    path('api/dashboard-data/', dashboard_data_api, name='dashboard_data'),
    path('api/top-products/', top_products_api, name='top_products'),
    path('api/customer-stats/', customer_stats_api, name='customer_stats'),

    # Reportes
    path('api/daily-report/', daily_report_view, name='daily_report_csv'),
    path('api/daily-report-pdf/', daily_report_pdf_view, name='daily_report_pdf'),
]
