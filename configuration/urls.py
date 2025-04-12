from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'settings', views.GlobalSettingsViewSet)
router.register(r'custom-fields/definitions', views.CustomFieldDefinitionViewSet)

app_name = 'configuration'

urlpatterns = [
    # Web UI URLs
    path('settings/', views.settings_view, name='settings'),
    path('custom-fields/', views.custom_fields_view, name='custom_fields'),
    path('custom-fields/add/', views.add_custom_field, name='add_custom_field'),
    path('custom-fields/edit/<int:field_id>/', views.edit_custom_field, name='edit_custom_field'),
    path('custom-fields/delete/<int:field_id>/', views.delete_custom_field, name='delete_custom_field'),

    # API URLs
    path('api/', include(router.urls)),
]