from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('registro/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('', views.home, name='home'),
    path('historial/', views.transaction_history, name='transaction_history'),
    path('estadisticas/', views.financial_statistics, name='financial_statistics'),
    path('analizar-habitos/', views.analizar_habitos, name='analizar_habitos'),
    path('ahorro/objetivo/', views.savings_goal, name='savings_goal'),

    path('ingreso/', views.income_register, name='income_register'),
    path('ingreso/eliminar/<int:id>/', views.income_delete, name='income_delete'),
    path('gasto/', views.expense_record, name='expense_record'),
    path('gasto/eliminar/<int:id>/', views.expense_delete, name='expense_delete'),

    path('presupuesto/', views.budget_create, name='budget_create'),
    path('presupuesto/restante/', views.remaining_budget, name='remaining_budget'),

    path('categorias/', views.manage_categories, name='manage_categories'),
    path('categorias/crear/', views.category_create, name='category_create'),
    path('categorias/editar/<int:id>/', views.category_edit, name='category_edit'),
    path('categorias/eliminar/<int:id>/', views.category_delete, name='category_delete'),
    path('categorias/<int:id>/editar/', views.category_edit),
    path('categorias/<int:id>/eliminar/', views.category_delete),

    path('reportes/pdf/', views.export_pdfpage, name='export_pdfpage'),
    path('reportes/pdf/download/', views.export_monthly_pdf, name='export_monthly_pdf'),
    path('reportes/excel/download/', views.export_monthly_excel, name='export_monthly_excel'),
    path('export/pdf/', views.export_pdfpage),
    path('export/pdf/download/', views.export_monthly_pdf),
    path('export/excel/download/', views.export_monthly_excel),
]
