from django.urls import path
from ecomapp import views
from .views import *
from . import views



app_name = "ecomapp"
urlpatterns = [

# coustumer side
    path("", views.home_view, name="home"),
    path("allproducts/", views.all_products_view, name="allproducts"),
    path("product/<slug:slug>/", views.product_detail_view, name="productdetail"),
    path("add-to-cart-<int:pro_id>/", views.add_to_cart, name="addtocart"),
    path("my-cart/", views.my_cart, name="mycart"),
    path("manage-cart/<int:cp_id>/", views.manage_cart, name="managecart"),
    path("empty-cart/", views.empty_cart, name="emptycart"),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('esewa-request/', views.esewa_request_view, name='esewarequest'),
    path('esewarequest/<int:o_id>/', views.esewa_request_view, name='esewarequest'),
    path('esewa-verify/', views.esewa_verify_view, name='esewaverify'),
    path('register/', views.customer_registration_view, name='customerregistration'),
    path('logout/', views.customer_logout_view, name='customerlogout'),
    path('login/', views.customer_login_view, name='customerlogin'),
    path('profile/', views.customer_profile_view, name="customer_profile"),
    path('order/<int:pk>/', views.customer_order_detail_view, name='customerorderdetail'),
    path('search/', views.search_view, name='search'),
    path('mail/',views.Helpdesk,name="ml"),
    path('change-username-password/', views.change_username_password, name='change_username_password'),
    path('submit-feedback/', views.submit_feedback, name='submit_feedback'),
    path('view-feedback/', views.view_feedback, name='view_feedback'),



#-------------------------------------------------------------------------------------------------------------------------------------------------------

# Admin Side pages
    path('admin-login/', views.admin_login_view, name='adminlogin'),
    path("admin-home/", views.admin_home_view, name="adminhome"),
    path("admin-order/<int:pk>/", views.admin_order_detail_view, name="adminorderdetail"),
    path("admin-all-orders/", views.admin_order_list_view, name="adminorderlist"),
    path("admin-order-<int:pk>-change/", views.admin_change_order_status, name="adminorderstatuschange"),
    path("admin-product/list/", views.admin_product_list_view, name="adminproductlist"),
    path("admin-product/add/", views.admin_create_product, name="adminproductcreate"),

    
    

]
