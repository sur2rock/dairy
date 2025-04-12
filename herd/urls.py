from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'buffalo', views.BuffaloViewSet)
router.register(r'breeds', views.BreedViewSet)
router.register(r'lifecycle', views.LifecycleEventViewSet)
router.register(r'milking', views.MilkProductionViewSet)

app_name = 'herd'

urlpatterns = [
    # Buffalo URLs
    path('buffalo/', views.buffalo_list, name='buffalo_list'),
    path('buffalo/add/', views.buffalo_add, name='buffalo_add'),
    path('buffalo/<int:buffalo_id>/', views.buffalo_detail, name='buffalo_detail'),
    path('buffalo/<int:buffalo_id>/edit/', views.buffalo_edit, name='buffalo_edit'),
    path('buffalo/<int:buffalo_id>/delete/', views.buffalo_delete, name='buffalo_delete'),

    # Breed URLs
    path('breeds/', views.breed_list, name='breed_list'),
    path('breeds/add/', views.breed_add, name='breed_add'),
    path('breeds/<int:breed_id>/edit/', views.breed_edit, name='breed_edit'),

    # Lifecycle Event URLs
    path('events/add/', views.lifecycle_event_add, name='lifecycle_event_add'),

    # Milk Production URLs
    path('milk/', views.milk_production_list, name='milk_production_list'),
    path('milk/add/', views.milk_production_add, name='milk_production_add'),
    path('milk/batch/', views.milk_production_batch, name='milk_production_batch'),
    path('milk/export/', views.export_milk_production, name='export_milk_production'),

    # API URLs
    path('api/', include(router.urls)),
]