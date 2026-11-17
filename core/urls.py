from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('shops/add/', views.add_shop, name='add_shop'),
    path('shops/', views.shops_list, name='shops_list'),
    path('shop/<int:shop_id>/', views.shop_detail, name='shop_detail'),
    path('shop/<int:shop_id>/edit/', views.edit_shop, name='edit_shop'),
    path('shop/<int:shop_id>/delete/', views.delete_shop, name='delete_shop'),
    path('supply/<int:supply_id>/edit/', views.edit_supply, name='edit_supply'),
    path('update-price/', views.update_price, name='update_price'),
    path('new-supply/', views.new_supply, name='new_supply'),
    path('new-payment/', views.new_payment, name='new_payment'),
]