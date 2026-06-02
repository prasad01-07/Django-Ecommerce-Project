from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal
from .models import Category, Product, Cart, CartItem, Order, OrderItem
from .forms import RegistrationForm, LoginForm, CheckoutForm


def get_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.save()
        cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


def index(request):
    featured = Product.objects.select_related('category').filter(is_available=True)[:4]
    latest = Product.objects.select_related('category').filter(is_available=True).order_by('-created_at')[:8]
    categories = Category.objects.all()
    context = {
        'featured': featured,
        'latest': latest,
        'categories': categories,
    }
    return render(request, 'store/index.html', context)


def category_list(request):
    categories = Category.objects.annotate(product_count=Count('products')).all()
    return render(request, 'store/category_list.html', {'categories': categories})


def category_detail(request, slug):
    category = get_object_or_404(Category.objects.annotate(product_count=Count('products')), slug=slug)
    return render(request, 'store/category_detail.html', {'category': category})


def product_list(request):
    products_list = Product.objects.select_related('category').filter(is_available=True)
    paginator = Paginator(products_list, 9)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    return render(request, 'store/product_list.html', {'products': products})


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category'), slug=slug, is_available=True
    )
    related = Product.objects.select_related('category').filter(
        category=product.category, is_available=True
    ).exclude(id=product.id)[:4]
    return render(request, 'store/product_detail.html', {'product': product, 'related': related})


def register(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('profile')
    else:
        form = RegistrationForm()
    return render(request, 'store/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('profile')
    else:
        form = LoginForm()
    return render(request, 'store/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('index')


@login_required
def profile(request):
    return render(request, 'store/profile.html', {'user': request.user})


def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)
    cart = get_cart(request)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    new_qty = item.quantity + 1 if not created else 1
    if new_qty > product.stock:
        messages.error(request, f'Sorry, only {product.stock} available.')
        return redirect(request.META.get('HTTP_REFERER', 'cart_detail'))
    item.quantity = new_qty
    item.save()
    messages.success(request, f'{product.name} added to cart.')
    return redirect(request.META.get('HTTP_REFERER', 'cart_detail'))


def cart_remove(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    if request.user.is_authenticated and item.cart.user == request.user:
        item.delete()
    elif item.cart.session_key == request.session.session_key:
        item.delete()
    messages.info(request, f'{item.product.name} removed from cart.')
    return redirect('cart_detail')


def cart_update(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    if request.method == 'POST':
        qty = int(request.POST.get('quantity', 1))
        if qty < 1:
            item.delete()
            messages.info(request, f'{item.product.name} removed from cart.')
        elif qty > item.product.stock:
            messages.error(request, f'Sorry, only {item.product.stock} of "{item.product.name}" available.')
        else:
            item.quantity = qty
            item.save()
            messages.success(request, 'Cart updated.')
    return redirect('cart_detail')


def cart_detail(request):
    cart = get_cart(request)
    return render(request, 'store/cart.html', {'cart': cart})


def checkout(request):
    cart = get_cart(request)
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart_detail')
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            for item in cart.items.all():
                if item.quantity > item.product.stock:
                    messages.error(request, f'"{item.product.name}" stock insufficient.')
                    return redirect('cart_detail')
            subtotal = cart.total()
            shipping_cost = Decimal('0') if subtotal >= Decimal('50') else Decimal('5.99')
            tax = (subtotal * Decimal('0.10')).quantize(Decimal('0.01'))
            total = (subtotal + shipping_cost + tax).quantize(Decimal('0.01'))
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                full_name=form.cleaned_data['full_name'],
                email=form.cleaned_data['email'],
                address=form.cleaned_data['address'],
                city=form.cleaned_data['city'],
                postal_code=form.cleaned_data['postal_code'],
                phone=form.cleaned_data['phone'],
                shipping_cost=shipping_cost,
                tax=tax,
                total=total,
            )
            for item in cart.items.all():
                product = item.product
                product.stock -= item.quantity
                product.save()
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=product.price,
                )
            cart.items.all().delete()
            messages.success(request, 'Order placed successfully!')
            return redirect('order_success', order_id=order.id)
    else:
        initial = {}
        if request.user.is_authenticated:
            initial = {
                'full_name': request.user.get_full_name(),
                'email': request.user.email,
            }
        form = CheckoutForm(initial=initial)
    subtotal = cart.total()
    shipping_cost = Decimal('0') if subtotal >= Decimal('50') else Decimal('5.99')
    tax = (subtotal * Decimal('0.10')).quantize(Decimal('0.01'))
    total = (subtotal + shipping_cost + tax).quantize(Decimal('0.01'))
    return render(request, 'store/checkout.html', {
        'form': form, 'cart': cart,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'tax': tax,
        'grand_total': total,
    })


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product')
    return render(request, 'store/order_history.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_detail.html', {'order': order})


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'store/order_success.html', {'order': order})


def search_products(request):
    query = request.GET.get('q', '').strip()
    results = Product.objects.none()
    if query:
        results = Product.objects.select_related('category').filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_available=True
        )
    paginator = Paginator(results, 9)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    return render(request, 'store/search_results.html', {
        'products': products,
        'query': query,
    })
