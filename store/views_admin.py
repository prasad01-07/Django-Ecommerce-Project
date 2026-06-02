from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum
from django.core.paginator import Paginator
from .models import Category, Product, Order, OrderItem
from .forms import CheckoutForm


@staff_member_required
def dashboard(request):
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_customers = User.objects.filter(is_staff=False).count()
    total_revenue = Order.objects.aggregate(Sum('total'))['total__sum'] or 0
    paid_orders = Order.objects.filter(paid=True).count()
    pending_orders = Order.objects.filter(paid=False).count()
    recent_orders = Order.objects.all()[:5]

    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'total_revenue': total_revenue,
        'paid_orders': paid_orders,
        'pending_orders': pending_orders,
        'recent_orders': recent_orders,
    }
    return render(request, 'admin_dashboard/dashboard.html', context)


@staff_member_required
def product_list(request):
    products = Product.objects.all()
    return render(request, 'admin_dashboard/product_list.html', {'products': products})


@staff_member_required
def product_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        is_available = request.POST.get('is_available') == 'on'
        category = get_object_or_404(Category, id=category_id)
        product = Product.objects.create(
            name=name, category=category, description=description,
            price=price, stock=stock, is_available=is_available,
        )
        if 'image' in request.FILES:
            product.image = request.FILES['image']
            product.save()
        messages.success(request, 'Product created.')
        return redirect('admin_product_list')
    categories = Category.objects.all()
    return render(request, 'admin_dashboard/product_form.html', {'categories': categories})


@staff_member_required
def product_update(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.category = get_object_or_404(Category, id=request.POST.get('category'))
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.stock = request.POST.get('stock')
        product.is_available = request.POST.get('is_available') == 'on'
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        product.save()
        messages.success(request, 'Product updated.')
        return redirect('admin_product_list')
    categories = Category.objects.all()
    return render(request, 'admin_dashboard/product_form.html', {'product': product, 'categories': categories})


@staff_member_required
def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, 'Product deleted.')
    return redirect('admin_product_list')


@staff_member_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'admin_dashboard/category_list.html', {'categories': categories})


@staff_member_required
def category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category = Category.objects.create(name=name, description=description)
        if 'image' in request.FILES:
            category.image = request.FILES['image']
            category.save()
        messages.success(request, 'Category created.')
        return redirect('admin_category_list')
    return render(request, 'admin_dashboard/category_form.html')


@staff_member_required
def category_update(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.description = request.POST.get('description')
        if 'image' in request.FILES:
            category.image = request.FILES['image']
        category.save()
        messages.success(request, 'Category updated.')
        return redirect('admin_category_list')
    return render(request, 'admin_dashboard/category_form.html', {'category': category})


@staff_member_required
def category_delete(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    messages.success(request, 'Category deleted.')
    return redirect('admin_category_list')


@staff_member_required
def order_list(request):
    orders = Order.objects.all()
    return render(request, 'admin_dashboard/order_list.html', {'orders': orders})


@staff_member_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        if 'toggle_paid' in request.POST:
            order.paid = not order.paid
            order.save()
            messages.success(request, f'Order #{order.id} payment status toggled.')
        elif 'status' in request.POST:
            order.status = request.POST['status']
            order.save()
            messages.success(request, f'Order #{order.id} status updated to {order.get_status_display()}.')
        return redirect('admin_order_detail', order_id=order.id)
    return render(request, 'admin_dashboard/order_detail.html', {'order': order})


@staff_member_required
def order_delete(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.delete()
    messages.success(request, 'Order deleted.')
    return redirect('admin_order_list')


@staff_member_required
def user_list(request):
    users = User.objects.all()
    return render(request, 'admin_dashboard/user_list.html', {'users': users})


@staff_member_required
def user_toggle_staff(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_staff = not user.is_staff
    user.save()
    messages.success(request, f'{user.username} staff status toggled.')
    return redirect('admin_user_list')


@staff_member_required
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, 'User deleted.')
    return redirect('admin_user_list')
