from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'expense-categories', views.ExpenseCategoryViewSet)
router.register(r'income-categories', views.IncomeCategoryViewSet)
router.register(r'expenses', views.ExpenseRecordViewSet)
router.register(r'income', views.IncomeRecordViewSet)
router.register(r'profitability', views.ProfitabilityViewSet)

app_name = 'finance'

urlpatterns = [
    # Expense Category URLs
    path('expense-categories/', views.expense_category_list, name='expense_category_list'),
    path('expense-categories/add/', views.expense_category_add, name='expense_category_add'),
    path('expense-categories/<int:category_id>/edit/', views.expense_category_edit, name='expense_category_edit'),

    # Income Category URLs
    path('income-categories/', views.income_category_list, name='income_category_list'),
    path('income-categories/add/', views.income_category_add, name='income_category_add'),
    path('income-categories/<int:category_id>/edit/', views.income_category_edit, name='income_category_edit'),

    # Expense URLs
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_add, name='expense_add'),
    path('expenses/<int:expense_id>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:expense_id>/delete/', views.expense_delete, name='expense_delete'),
    path('expenses/export/', views.export_expenses, name='export_expenses'),

    # Income URLs
    path('income/', views.income_list, name='income_list'),
    path('income/add/', views.income_add, name='income_add'),
    path('income/<int:income_id>/edit/', views.income_edit, name='income_edit'),
    path('income/<int:income_id>/delete/', views.income_delete, name='income_delete'),
    path('income/export/', views.export_income, name='export_income'),
    path('income/generate-milk-income/', views.milk_income_generator, name='milk_income_generator'),

    # Profitability URLs
    path('profitability/', views.profitability, name='profitability'),
    path('profitability/calculate/', views.calculate_profitability, name='calculate_profitability'),

    # API URLs
    path('api/', include(router.urls)),
]