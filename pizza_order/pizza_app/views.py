from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.conf import settings
from .models import Category, Product, Order, OrderItem
from .cart import Cart
from .forms import OrderForm
import stripe
import json

# Create your views here.


stripe.api_key = settings.STRIPE_SECRET_KEY

def index(request):
    categories = Category.objects.all()
    return render(request, 'pizza_app/index.html', {
        'categories': categories,
        'products': Product.objects.filter(available=True),
        'stripe_public_key': settings.STRIPE_PUBLISHABLE_KEY
    })

def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    return render(request, 'pizza_app/product_detail.html', {
        'product': product
    })

@require_POST
def cart_add(request):
    cart = Cart(request)
    data = json.loads(request.body)
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    product = get_object_or_404(Product, id=product_id)
    cart.add(product=product, quantity=quantity)
    return JsonResponse({
        'status': 'success',
        'cart_total': len(cart),
        'cart_price': float(cart.get_total_price())
    })

@require_POST
def cart_remove(request):
    cart = Cart(request)
    data = json.loads(request.body)
    product_id = data.get('product_id')
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return JsonResponse({
        'status': 'success',
        'cart_total': len(cart),
        'cart_price': float(cart.get_total_price())
    })

@require_POST
def cart_update(request):
    cart = Cart(request)
    data = json.loads(request.body)
    product_id = data.get('product_id')
    quantity = int(data.get('quantity'))
    
    if quantity > 0:
        cart.update_quantity(product_id, quantity)
    else:
        product = get_object_or_404(Product, id=product_id)
        cart.remove(product)
        
    return JsonResponse({
        'status': 'success',
        'cart_total': len(cart),
        'cart_price': float(cart.get_total_price())
    })

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'pizza_app/cart.html', {'cart': cart})

def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('pizza_app:index')
        
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.save()
            
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )
            
            # Create Stripe session
            try:
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f'Order #{order.id}',
                            },
                            'unit_amount': int(cart.get_total_price() * 100),
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=request.build_absolute_uri(
                        reverse('pizza_app:order_confirmation', kwargs={'order_id': order.id})
                    ),
                    cancel_url=request.build_absolute_uri(
                        reverse('pizza_app:order_failure', kwargs={'order_id': order.id})
                    ),
                )
                
                # Update order with Stripe ID
                order.stripe_id = checkout_session.id
                order.save()
                
                # Clear the cart
                cart.clear()
                
                return redirect(checkout_session.url, code=303)
                
            except Exception as e:
                return render(request, 'pizza_app/checkout.html', {
                    'form': form,
                    'error': str(e)
                })
    else:
        form = OrderForm()
    
    return render(request, 'pizza_app/checkout.html', {
        'form': form,
        'cart': cart,
        'stripe_public_key': settings.STRIPE_PUBLISHABLE_KEY
    })

def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Verify payment with Stripe (in a real app, this would be handled by a webhook)
    if not order.paid:
        try:
            session = stripe.checkout.Session.retrieve(order.stripe_id)
            if session.payment_status == 'paid':
                order.paid = True
                order.save()
        except Exception:
            pass
    
    return render(request, 'pizza_app/order_confirmation.html', {'order': order})

def order_failure(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'pizza_app/order_failure.html', {'order': order})

# Stripe webhook handling (simplified for this example)
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            order_id = session.get('client_reference_id')
            if order_id:
                order = Order.objects.get(id=order_id)
                order.paid = True
                order.save()
        
        return HttpResponse(status=200)
    except Exception as e:
        return HttpResponse(status=400)

#about page for pizza app
def about(request):
    return render(request, 'pizza_app/about.html')