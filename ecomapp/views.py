from django.views.generic import  CreateView, FormView, DetailView, ListView,View, TemplateView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.db.models import Q
from .models import *
from .forms import *
import requests
from functools import wraps
import xml.etree.ElementTree as ET
from django.contrib.auth import update_session_auth_hash




def home_view(request):
    template_name = "home.html"
    context = {}
    context['product_list'] = Product.objects.all().order_by("id")
    return render(request, template_name, context)

def all_products_view(request):
    template_name = "allproducts.html"
    context = {}
    context['allcategories'] = Category.objects.all()
    return render(request, template_name, context)
    
def product_detail_view(request, slug):
    template_name = "productdetail.html"
    context = {}
    
    product = Product.objects.get(slug=slug)
    product.view_count += 1
    product.save()
    
    context['product'] = product
    
    return render(request, template_name, context)

def add_to_cart(request, pro_id):
    # Get product
    product_obj = Product.objects.get(id=pro_id)

    # Check if cart exists
    cart_id = request.session.get("cart_id")
    if cart_id:
        cart_obj = Cart.objects.get(id=cart_id)
        this_product_in_cart = cart_obj.cartproduct_set.filter(product=product_obj)

        # Item already exists in cart
        if this_product_in_cart.exists():
            cartproduct = this_product_in_cart.last()
            cartproduct.quantity += 1
            cartproduct.subtotal += product_obj.selling_price
            cartproduct.save()
            cart_obj.total += product_obj.selling_price
            cart_obj.save()
        # New item is added to the cart
        else:
            cartproduct = CartProduct.objects.create(
                cart=cart_obj, product=product_obj, rate=product_obj.selling_price, quantity=1, subtotal=product_obj.selling_price)
            cart_obj.total += product_obj.selling_price
            cart_obj.save()

    else:
        cart_obj = Cart.objects.create(total=0)
        request.session['cart_id'] = cart_obj.id
        cartproduct = CartProduct.objects.create(
            cart=cart_obj, product=product_obj, rate=product_obj.selling_price, quantity=1, subtotal=product_obj.selling_price)
        cart_obj.total += product_obj.selling_price
        cart_obj.save()

    return render(request, "addtocart.html", {})

def manage_cart(request, cp_id):
    action = request.GET.get("action")
    cp_obj = CartProduct.objects.get(id=cp_id)
    cart_obj = cp_obj.cart

    if action == "inc":
        cp_obj.quantity += 1
        cp_obj.subtotal += cp_obj.rate
        cp_obj.save()
        cart_obj.total += cp_obj.rate
        cart_obj.save()
    elif action == "dcr":
        cp_obj.quantity -= 1
        cp_obj.subtotal -= cp_obj.rate
        cp_obj.save()
        cart_obj.total -= cp_obj.rate
        cart_obj.save()
        if cp_obj.quantity == 0:
            cp_obj.delete()
    elif action == "rmv":
        cart_obj.total -= cp_obj.subtotal
        cart_obj.save()
        cp_obj.delete()
    else:
        pass

    return redirect("ecomapp:mycart")

def empty_cart(request):
    cart_id = request.session.get("cart_id", None)
    if cart_id:
        cart = Cart.objects.get(id=cart_id)
        cart.cartproduct_set.all().delete()
        cart.total = 0
        cart.save()
    return redirect("ecomapp:mycart")

def my_cart(request):
    cart_id = request.session.get("cart_id", None)
    cart = None
    if cart_id:
        cart = Cart.objects.get(id=cart_id)
    return render(request, "mycart.html", {"cart": cart})

class Ecom(object):
    def dispatch(self, request, *args, **kwargs):
        cart_id = request.session.get("cart_id")
        if cart_id:
            cart_obj = Cart.objects.get(id=cart_id)
            if request.user.is_authenticated and request.user.customer:
                cart_obj.customer = request.user.customer
                cart_obj.save()
        return super().dispatch(request, *args, **kwargs)

class CheckoutView(Ecom, CreateView):
    template_name = "checkout.html"
    form_class = CheckoutForm
    success_url = reverse_lazy("ecomapp:home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.customer:
            pass
        else:
            return redirect("/login/?next=/checkout/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_id = self.request.session.get("cart_id", None)
        if cart_id:
            cart_obj = Cart.objects.get(id=cart_id)
        else:
            cart_obj = None
        context['cart'] = cart_obj
        return context

    def form_valid(self, form):
        cart_id = self.request.session.get("cart_id")
        if cart_id:
            cart_obj = Cart.objects.get(id=cart_id)
            form.instance.cart = cart_obj
            form.instance.subtotal = cart_obj.total
            form.instance.total = cart_obj.total
            form.instance.order_status = "order processing"
            del self.request.session['cart_id']
            pm = form.cleaned_data.get("payment_method")
            order = form.save()

            # Send an email to the customer
            subject = 'Order Confirmation'
            message = 'Thank you for your orders. Your order will delivered in 3 days!.'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [self.request.user.email]  # Use the user's email or any other recipient email
            send_mail(subject, message, from_email, recipient_list, fail_silently=True)

            if pm == "Esewa":
                return redirect(reverse("ecomapp:esewarequest") + "?o_id=" + str(order.id))
        else:
            return redirect("ecomapp:home")
        return super().form_valid(form)
    
def esewa_request_view(request):
    o_id = request.GET.get("o_id")
    order = Order.objects.get(id=o_id)
    context = {
        "order": order
    }
    return render(request, "esewarequest.html", context)

def esewa_verify_view(request):
    oid = request.GET.get("oid")
    amt = request.GET.get("amt")
    refId = request.GET.get("refId")

    url = "https://uat.esewa.com.np/epay/transrec"
    d = {
        'amt': amt,
        'scd': 'epay_payment',
        'rid': refId,
        'pid': oid,
    }
    resp = requests.post(url, d)
    root = ET.fromstring(resp.content)
    status = root[0].text.strip()

    order_id = oid.split("_")[1]
    order_obj = Order.objects.get(id=order_id)

    if status == "Success":
        order_obj.payment_completed = True
        order_obj.save()
        return redirect("/")
    else:
        return redirect("/esewa-request/?o_id=" + order_id)

def customer_registration_view(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            email = form.cleaned_data.get("email")
            
            # Create a new user
            user = User.objects.create_user(username, email, password)
            
            # Create a new customer associated with the user
            customer = Customer.objects.create(user=user)
            login(request, user)
            
            return redirect(get_success_url(request))
    else:
        form = CustomerRegistrationForm()

    return render(request, "customerregistration.html", {'form': form})

def customer_login_view(request):
    if request.method == 'POST':
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect(get_success_url(request))
            else:
                pass
    else:
        form = CustomerLoginForm()

    return render(request, "customerlogin.html", {'form': form})

def customer_logout_view(request):
    logout(request)
    return redirect("ecomapp:home")

def get_success_url(request):
    if "next" in request.GET:
        next_url = request.GET.get("next")
        return next_url
    else:
        return reverse_lazy("ecomapp:home")

@login_required
def customer_profile_view(request):
    customer = request.user.customer
    orders = Order.objects.filter(cart__customer=customer).order_by("-id")
    
    if request.method == 'POST':
        form = CustomerEditForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
        return redirect('ecomapp:customer_profile')
    else:
        form = CustomerEditForm(instance=customer)
    
    context = {
        'customer': customer,
        'orders': orders,
        'form': form,
    }
    return render(request, 'customerprofile.html', context)

    
@login_required
def customer_order_detail_view(request, pk):

    if not request.user.customer:
        return redirect("/login/?next=/profile/")

    order = Order.objects.get( id=pk)

    if request.user.customer != order.cart.customer:
        return redirect("ecomapp:customerprofile")

    context = {
        'ord_obj': order,
    }
    return render(request, 'customerorderdetail.html', context)



def search_view(request):
    kw = request.GET.get("keyword")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    results = Product.objects.filter(
        Q(title__icontains=kw) | Q(description__icontains=kw) | Q(return_policy__icontains=kw))

    if min_price and max_price:
        results = results.filter(price__gte=min_price, price__lte=max_price)

    context = {
        "results": results,
    }
    return render(request, 'search.html', context)


def Helpdesk(request):
	if request.method == "POST":
		sndr=request.POST['sn']
		sbj=request.POST['sb']
		m = request.POST['msg']
		t = settings.EMAIL_HOST_USER
		b = send_mail(sbj,m,t,[sndr])
		if b == 1:
			messages.success(request,"Message sent Successfully")
			return redirect('/mail')
		else:
			messages.warning(request,"Message not sent")
			return redirect('/mail')
	return render(request,'helpdesk.html')



@login_required
def change_username_password(request):
    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            new_username = form.cleaned_data.get('new_username')
            new_password = form.cleaned_data.get('new_password')

            # Change username if provided
            if new_username:
                request.user.username = new_username
                request.user.save()

            # Change password if provided
            if new_password:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)  # Important to avoid logging the user out

            return redirect('ecomapp:customer_profile')
    else:
        form = CustomUserForm()

    context = {'form': form}
    return render(request, 'change_username_password.html', context)

def submit_feedback(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            feedback.save()
            return redirect('ecomapp:view_feedback') 
    else:
        form = FeedbackForm()
    
    return render(request, 'feedback_form.html', {'form': form})

def view_feedback(request):
    feedback_list = Feedback.objects.all()
    return render(request, 'feedback_list.html', {'feedback_list': feedback_list})



#-----------------------------------------------------------------------------------------------------------------------------------------------

# admin pages

def admin_login_view(request):
    if request.method == 'POST':
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            uname = form.cleaned_data.get("username")
            pword = form.cleaned_data["password"]
            usr = authenticate(username=uname, password=pword)
            if usr is not None and Admin.objects.filter(user=usr).exists():
                login(request, usr)
                return redirect(reverse_lazy("ecomapp:adminhome"))
            else:
                error = "Invalid credentials"
    else:
        form = CustomerLoginForm()
        error = None

    return render(request, "adminpages/adminlogin.html", {"form": form, "error": error})

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and Admin.objects.filter(user=request.user).exists():
            return view_func(request, *args, **kwargs)
        else:
            return redirect("/admin-login/")
    
    return _wrapped_view

@admin_required
def admin_home_view(request):
    return render(request, "adminpages/adminhome.html")

@admin_required
def admin_order_detail_view(request, pk):
    try:
        ord_obj = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return redirect("/admin-home/")  

    all_status = ORDER_STATUS  

    context = {
        "ord_obj": ord_obj,
        "allstatus": all_status,
    }

    return render(request, "adminpages/adminorderdetail.html", context)

@admin_required
def admin_order_list_view(request):
    all_orders = Order.objects.all().order_by("-id")

    context = {
        "allorders": all_orders,
    }

    return render(request, "adminpages/adminorderlist.html", context)

@admin_required
def admin_change_order_status(request, pk):
    if request.method == "POST":
        order_obj = Order.objects.get( id=pk)
        new_status = request.POST.get("status")
        order_obj.order_status = new_status
        order_obj.save()
        return redirect(reverse_lazy("ecomapp:adminorderdetail", kwargs={"pk": pk}))
    else:
        return redirect(reverse_lazy("ecomapp:adminhome"))  


@admin_required
def admin_product_list_view(request):
    all_products = Product.objects.all().order_by("-id")

    context = {
        "allproducts": all_products,
    }

    return render(request, "adminpages/adminproductlist.html", context)


@admin_required
def admin_create_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            images = request.FILES.getlist("more_images")
            for image in images:
                ProductImage.objects.create(product=product, image=image)
            return redirect(reverse_lazy("ecomapp:adminproductlist"))
    else:
        form = ProductForm()
    
    context = {
        "form": form,
    }

    return render(request, "adminpages/adminproductcreate.html", context)
   


