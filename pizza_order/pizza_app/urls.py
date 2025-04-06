from django.urls import path
from . import views

app_name = 'pizza_app'

urlpatterns = [
    path('', views.index, name='index'),
    path('product/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/', views.cart_add, name='cart_add'),
    path('cart/remove/', views.cart_remove, name='cart_remove'),
    path('cart/update/', views.cart_update, name='cart_update'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/confirmation/<uuid:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('order/failure/<uuid:order_id>/', views.order_failure, name='order_failure'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('about/', views.about, name='about'),
]