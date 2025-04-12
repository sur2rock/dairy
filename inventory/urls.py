from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'fodder-types', views.FodderTypeViewSet)
router.register(r'levels', views.FeedInventoryViewSet)
router.register(r'purchases', views.FeedPurchaseViewSet)
router.register(r'consumption', views.FeedConsumptionViewSet)
router.register(r'in-house-production', views.InHouseFeedProductionViewSet)

app_name = 'inventory'

urlpatterns = [
    # Fodder Type URLs
    path('fodder-types/', views.fodder_type_list, name='fodder_type_list'),
    path('fodder-types/add/', views.fodder_type_add, name='fodder_type_add'),
    path('fodder-types/<int:fodder_type_id>/', views.fodder_type_detail, name='fodder_type_detail'),
    path('fodder-types/<int:fodder_type_id>/edit/', views.fodder_type_edit, name='fodder_type_edit'),

    # Inventory URLs
    path('levels/', views.inventory_list, name='inventory_list'),
    path('levels/<int:inventory_id>/adjust/', views.inventory_adjust, name='inventory_adjust'),

    # Purchase URLs
    path('purchases/', views.purchase_list, name='purchase_list'),
    path('purchases/add/', views.purchase_add, name='purchase_add'),
    path('purchases/<int:purchase_id>/edit/', views.purchase_edit, name='purchase_edit'),
    path('purchases/<int:purchase_id>/delete/', views.purchase_delete, name='purchase_delete'),

    # Consumption URLs
    path('consumption/', views.consumption_list, name='consumption_list'),
    path('consumption/add/', views.consumption_add, name='consumption_add'),
    path('consumption/<int:consumption_id>/edit/', views.consumption_edit, name='consumption_edit'),
    path('consumption/<int:consumption_id>/delete/', views.consumption_delete, name='consumption_delete'),

    # In-House Production URLs
    path('production/', views.production_list, name='production_list'),
    path('production/add/', views.production_add, name='production_add'),
    path('production/<int:production_id>/edit/', views.production_edit, name='production_edit'),
    path('production/<int:production_id>/delete/', views.production_delete, name='production_delete'),

    # API URLs
    path('api/', include(router.urls)),
]