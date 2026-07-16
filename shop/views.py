from decimal import Decimal
from datetime import timedelta
from functools import wraps
import json
from urllib.parse import quote
from uuid import uuid4
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, IntegerField, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
import stripe
from .models import BlogPost, Category, CustomerMessage, Order, OrderItem, Product, Reservation, Review, GalleryImage, NewsletterSubscriber, LoyaltyReward, Favorite, ProductTranslation, CategoryTranslation, DiningTable, StaffMember, StaffShift, PurchaseOrder
from .translations import PAGE_SLUGS, HOME_SLUGS, TRANSLATIONS, get_lang_from_path


def _password_matches(raw_password, configured_password):
    return bool(raw_password) and raw_password == configured_password


def _session_or_staff(request, key):
    return bool(request.session.get(key) or request.user.is_staff)


def kitchen_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if _session_or_staff(request, 'kitchen_access') or _session_or_staff(request, 'owner_access'):
            return view_func(request, *args, **kwargs)
        login_url = reverse('shop:kitchen_login')
        return redirect(f'{login_url}?next={quote(request.get_full_path())}')
    return wrapped


def owner_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if _session_or_staff(request, 'owner_access'):
            return view_func(request, *args, **kwargs)
        login_url = reverse('shop:owner_login')
        return redirect(f'{login_url}?next={quote(request.get_full_path())}')
    return wrapped


def _today_bounds():
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


def _menu_category_order(qs):
    return qs.annotate(
        menu_priority=Case(
            When(name__iexact='Nos Pizza', then=0),
            When(name__iexact='Nos Pizzas', then=0),
            When(name__iexact='Nos Pasta', then=1),
            When(name__iexact='Nos Pastas', then=1),
            When(name__icontains='raviol', then=2),
            When(name__icontains='entrée', then=3),
            When(name__icontains='entree', then=3),
            When(name__icontains='antipasti', then=4),
            When(name__icontains='bruschetta', then=5),
            When(name__icontains='salade', then=6),
            When(name__icontains='bambino', then=7),
            When(name__icontains='douceur', then=8),
            When(name__icontains='suppl', then=9),
            When(name__icontains='pizza', then=0),
            When(name__icontains='pasta', then=1),
            When(name__icontains='aperitivo', then=20),
            When(name__icontains='digestif', then=21),
            When(name__icontains='birre', then=22),
            When(name__icontains='analcolici', then=23),
            When(name__icontains='caff', then=24),
            When(name__icontains='vin', then=25),
            default=30,
            output_field=IntegerField(),
        )
    ).order_by('menu_priority', 'order', 'name')


MENU_GROUPS = [
    {
        'slug': 'pizzas',
        'title': 'Nos Pizza',
        'eyebrow': 'Pizza',
        'summary': 'Toutes les pizzas maison avec les suppléments pour personnaliser votre commande.',
        'kind': 'is-pizza',
        'image': '/media/gallery/2eef003fea54537e5b8f6516f9fcec6ac5afe20b.jpeg',
        'matches': ('pizza', 'suppl'),
    },
    {
        'slug': 'pastas',
        'title': 'Nos Pastas',
        'eyebrow': 'Pasta',
        'summary': 'Pastas italiennes, ravioles et recettes généreuses servies bien chaudes.',
        'kind': 'is-pasta',
        'image': 'https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?auto=format&fit=crop&w=1200&q=82',
        'matches': ('pasta', 'raviol'),
    },
    {
        'slug': 'antipasti',
        'title': 'Entrées & Antipasti',
        'eyebrow': 'À partager',
        'summary': 'Entrées, antipasti, bruschette et salades pour commencer ou partager.',
        'kind': 'is-antipasti',
        'image': 'https://images.unsplash.com/photo-1546549032-9571cd6b27df?auto=format&fit=crop&w=1200&q=82',
        'matches': ('entrée', 'entree', 'antipasti', 'bruschetta', 'salade'),
    },
    {
        'slug': 'bambino',
        'title': 'Menu Bambino',
        'eyebrow': 'Enfants',
        'summary': 'Un menu simple et gourmand pensé pour les plus jeunes.',
        'kind': 'is-kids',
        'image': 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=1200&q=82',
        'matches': ('bambino',),
    },
    {
        'slug': 'douceurs',
        'title': 'Nos douceurs',
        'eyebrow': 'Desserts',
        'summary': 'Tiramisu, panna cotta, glaces et desserts italiens.',
        'kind': 'is-dessert',
        'image': 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?auto=format&fit=crop&w=1200&q=82',
        'matches': ('douceur', 'dessert', 'glace'),
    },
    {
        'slug': 'boissons',
        'title': 'Boissons',
        'eyebrow': 'Bar',
        'summary': 'Softs, bières, vins, apéritifs, digestifs, cafés et thés.',
        'kind': 'is-drink',
        'image': '/media/gallery/45e8414417d58a2774dc544f972c5d7a773a39e2.jpeg',
        'matches': ('aperitivo', 'digestif', 'birre', 'analcolici', 'caff', 'vin'),
    },
]


def _category_key(category):
    return f'{category.name} {category.slug}'.lower()


def _categories_for_group(group):
    categories = list(_menu_category_order(Category.objects.filter(is_active=True)))
    return [category for category in categories if any(match in _category_key(category) for match in group['matches'])]


def _menu_groups():
    groups = []
    for group in MENU_GROUPS:
        categories = _categories_for_group(group)
        if not categories:
            continue
        item = group.copy()
        item['url'] = reverse('shop:menu_group', args=[group['slug']])
        item['count'] = sum(category.products.filter(is_available=True).count() for category in categories)
        groups.append(item)
    return groups


def _menu_group_by_slug(slug):
    for group in MENU_GROUPS:
        if group['slug'] == slug:
            return group
    return None


def _apply_menu_translations(products, categories, lang):
    if lang == 'fr':
        return
    product_map = {tr.product_id: tr for tr in ProductTranslation.objects.filter(language=lang, product_id__in=[p.id for p in products])}
    category_map = {tr.category_id: tr for tr in CategoryTranslation.objects.filter(language=lang, category_id__in=[c.id for c in categories])}
    for product in products:
        tr = product_map.get(product.id)
        product.translated_name = tr.name if tr else product.name
        product.translated_description = tr.description if tr and tr.description else product.description
        if product.category_id and product.category_id in category_map:
            product.translated_category_name = category_map[product.category_id].name
    for category in categories:
        tr = category_map.get(category.id)
        category.translated_name = tr.name if tr else category.name
        category.translated_description = tr.description if tr and tr.description else category.description

def _customer_pizza_count(user):
    if not user.is_authenticated:
        return 0
    count = 0
    orders = Order.objects.filter(user=user).prefetch_related('items__product__category')
    for order in orders:
        if order.status in ['cancelled', 'refunded']:
            continue
        for item in order.items.all():
            category_name = (item.product.category.name if item.product and item.product.category else '').lower()
            item_name = (item.name or '').lower()
            if 'pizza' in category_name or 'pizza' in item_name:
                count += item.quantity
    return count

def _cart_items(request):
    cart = request.session.get('cart', {})
    products = Product.objects.filter(id__in=cart.keys(), is_available=True).select_related('category')
    items, total = [], Decimal('0.00')
    for p in products:
        qty = max(1, int(cart.get(str(p.id), 1)))
        line = p.price * qty
        total += line
        items.append({'product': p, 'qty': qty, 'line_total': line})
    return items, total

def _format_order_lines(order):
    return '\n'.join(
        f'- {item.quantity} x {item.name}: {item.line_total} EUR'
        for item in order.items.all()
    )

def _send_order_email(order, subject, intro):
    if not order.email:
        return False
    order_url = settings.SITE_URL.rstrip('/') + order.get_absolute_url()
    location_line = f'Table: {order.table_number}' if order.table_number else 'Type: retrait / sur place selon votre commande'
    body = (
        f'Bonjour {order.customer_name},\n\n'
        f'{intro}\n\n'
        f'Commande: {order.order_number}\n'
        f'{location_line}\n\n'
        f'Detail de la commande:\n{_format_order_lines(order)}\n\n'
        f'Total: {order.total} EUR\n'
        f'Suivi / facture: {order_url}\n\n'
        'Merci,\nPizza Vitti'
    )
    try:
        return send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [order.email], fail_silently=True) > 0
    except Exception:
        return False

def _send_order_received_email(order):
    sent = _send_order_email(
        order,
        f'Pizza Vitti - commande recue {order.order_number}',
        'Nous avons bien recu votre commande. Elle arrive dans le tableau de preparation Pizza Vitti.',
    )
    if sent:
        order.confirmation_email_sent = True
        order.save(update_fields=['confirmation_email_sent'])

def _send_order_ready_email(order):
    if order.ready_email_sent:
        return
    sent = _send_order_email(
        order,
        f'Pizza Vitti - votre commande est prete {order.order_number}',
        'Votre commande est prete. Vous pouvez la recuperer, ou elle va etre servie a votre table.',
    )
    if sent:
        order.ready_email_sent = True
        order.save(update_fields=['ready_email_sent'])

def _whatsapp_number(raw):
    digits = ''.join(ch for ch in (raw or '') if ch.isdigit())
    if not digits:
        return ''
    if digits.startswith('00'):
        digits = digits[2:]
    if digits.startswith('0') and len(digits) == 10:
        digits = '33' + digits[1:]
    return digits

def _whatsapp_customer_url(order, kind):
    phone = _whatsapp_number(order.phone)
    if not phone:
        return ''
    order_url = settings.SITE_URL.rstrip('/') + order.get_absolute_url()
    if kind == 'ready':
        message = (
            f'Bonjour {order.customer_name}, votre commande Pizza Vitti {order.order_number} est prête. '
            f'Vous pouvez la récupérer ou elle va être servie à votre table. Suivi: {order_url}'
        )
    else:
        message = (
            f'Bonjour {order.customer_name}, nous avons bien reçu votre commande Pizza Vitti {order.order_number}. '
            f'Elle est envoyée en préparation. Suivi: {order_url}'
        )
    return f'https://wa.me/{phone}?text={quote(message)}'

def _pizza_qty(items):
    pizza_words = ('pizza', 'pizzas')
    count = 0
    for item in items:
        product = item['product']
        category_name = (product.category.name if product.category else '').lower()
        product_name = product.name.lower()
        if any(word in category_name or word in product_name for word in pizza_words):
            count += item['qty']
    return count

def home(request):
    reviews = Review.objects.filter(is_published=True)[:6]
    gallery = GalleryImage.objects.filter(is_active=True)[:8]
    posts = BlogPost.objects.filter(is_published=True)[:3]
    menu_groups = _menu_groups()
    favorite_product_ids = set()
    if request.user.is_authenticated:
        favorite_product_ids = set(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    return render(request, 'shop/home.html', {
        'menu_groups': menu_groups, 'reviews': reviews, 'gallery': gallery, 'posts': posts, 'favorite_product_ids': favorite_product_ids,
        'meta_title': "Pizza Vitti Bordeaux | Pizzeria italienne et commande en ligne",
        'meta_description': "Pizza Vitti à Bordeaux : pizzas italiennes, menu en ligne, réservation, retrait et paiement en avance."
    })

def about(request):
    return redirect('shop:home')

def faq(request):
    return render(request, 'shop/faq.html', {'meta_title': "FAQ | Commandes Pizza Vitti"})

def boutique(request):
    qs = Product.objects.filter(is_available=True).select_related('category')
    query = request.GET.get('q','').strip()
    if query:
        qs = qs.filter(Q(name__icontains=query)|Q(description__icontains=query)|Q(category__name__icontains=query))
    paginator = Paginator(qs, 120)
    page_obj = paginator.get_page(request.GET.get('page'))
    lang = get_lang_from_path(request.path)
    _apply_menu_translations(list(page_obj.object_list), [], lang)
    favorite_product_ids = set()
    if request.user.is_authenticated:
        favorite_product_ids = set(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    return render(request, 'shop/boutique.html', {'page_obj': page_obj, 'query': query, 'favorite_product_ids': favorite_product_ids, 'menu_groups': _menu_groups()})

def category(request, slug):
    cat = get_object_or_404(Category, slug=slug, is_active=True)
    qs = cat.products.filter(is_available=True)
    paginator = Paginator(qs, 120)
    page_obj = paginator.get_page(request.GET.get('page'))
    lang = get_lang_from_path(request.path)
    _apply_menu_translations(list(page_obj.object_list), [cat], lang)
    favorite_product_ids = set()
    if request.user.is_authenticated:
        favorite_product_ids = set(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    return render(request, 'shop/boutique.html', {'page_obj': page_obj, 'category': cat, 'favorite_product_ids': favorite_product_ids, 'menu_groups': _menu_groups()})

def menu_group(request, group):
    menu_group_data = _menu_group_by_slug(group)
    if not menu_group_data:
        return redirect('shop:boutique')
    categories = _categories_for_group(menu_group_data)
    products = list(Product.objects.filter(is_available=True, category__in=categories).select_related('category'))
    lang = get_lang_from_path(request.path)
    _apply_menu_translations(products, categories, lang)
    sections = []
    for category in categories:
        section_products = [product for product in products if product.category_id == category.id]
        if section_products:
            sections.append({'category': category, 'products': section_products})
    favorite_product_ids = set()
    if request.user.is_authenticated:
        favorite_product_ids = set(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    return render(request, 'shop/boutique.html', {
        'menu_group': menu_group_data,
        'menu_groups': _menu_groups(),
        'group_sections': sections,
        'favorite_product_ids': favorite_product_ids,
        'meta_title': f"{menu_group_data['title']} | Pizza Vitti Bordeaux",
        'meta_description': menu_group_data['summary'],
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_available=True)
    lang = get_lang_from_path(request.path)
    _apply_menu_translations([product], [product.category] if product.category else [], lang)
    favorite_product_ids = set()
    if request.user.is_authenticated:
        favorite_product_ids = set(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    return render(request, 'shop/product_detail.html', {'product': product, 'favorite_product_ids': favorite_product_ids,
        'meta_title': product.meta_title or f'{product.name} | Pizza Vitti',
        'meta_description': product.meta_description or product.description[:155]})

def table_menu(request, table):
    table_number = ''.join(ch for ch in str(table) if ch.isalnum() or ch in '-_')[:20]
    if table_number:
        request.session['table_number'] = table_number
        messages.success(request, f'Table {table_number} sélectionnée. Choisissez vos plats, puis validez votre commande.')
    return redirect('shop:boutique')

@require_POST
def add_to_cart(request, product_id):
    get_object_or_404(Product, id=product_id, is_available=True)
    cart = request.session.get('cart', {})
    qty = max(1, int(request.POST.get('qty', 1)))
    cart[str(product_id)] = int(cart.get(str(product_id), 0)) + qty
    request.session['cart'] = cart
    messages.success(request, 'Plat ajouté au panier.')
    return redirect(request.POST.get('next') or 'shop:cart')

def cart(request):
    items, total = _cart_items(request)
    pizza_qty = _pizza_qty(items)
    return render(request, 'shop/cart.html', {
        'items': items, 'total': total, 'pizza_qty': pizza_qty,
        'loyalty_remaining': max(0, 5 - pizza_qty),
        'loyalty_gift_eligible': pizza_qty >= 5,
        'table_number': request.session.get('table_number', '').strip(),
    })

@require_POST
def update_cart(request):
    cart = {}
    for key, val in request.POST.items():
        if key.startswith('qty_'):
            try: qty = int(val)
            except ValueError: qty = 0
            if qty > 0: cart[key[4:]] = qty
    request.session['cart'] = cart
    messages.success(request, 'Panier mis à jour.')
    return redirect('shop:cart')

@require_POST
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    cart.pop(str(product_id), None)
    request.session['cart'] = cart
    messages.success(request, 'Plat retiré du panier.')
    return redirect(request.POST.get('next') or 'shop:cart')

def checkout(request):
    items, total = _cart_items(request)
    if not items:
        messages.error(request, 'Votre panier est vide.')
        return redirect('shop:boutique')
    table_number = request.session.get('table_number', '').strip()
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'stripe')
        order_type = 'dine_in' if table_number else request.POST.get('order_type', 'pickup')
        loyalty_reward = LoyaltyReward.objects.filter(is_active=True).first() if _pizza_qty(items) >= 5 else None
        selected_reward = loyalty_reward.get_reward_type_display() if loyalty_reward else ''
        loyalty_note = 'Cadeau fidélité à préparer.' if _pizza_qty(items) >= 5 else ''
        order = Order.objects.create(
            order_number='PV-' + uuid4().hex[:8].upper(),
            user=request.user if request.user.is_authenticated else None,
            customer_type='particulier',
            customer_name=request.POST.get('name','').strip(), email=request.POST.get('email','').strip(),
            phone=request.POST.get('phone','').strip(), table_number=table_number, address=request.POST.get('address','').strip(), order_type=order_type, selected_reward=selected_reward, promo_code=request.POST.get('promo_code','').strip(),
            notes=(request.POST.get('notes','').strip() + (f'\nOffre fidélité: {loyalty_note}' if loyalty_note else '')).strip(), total=total,
            payment_status='pending' if payment_method == 'stripe' else 'cash')
        for item in items:
            OrderItem.objects.create(order=order, product=item['product'], name=item['product'].name,
                quantity=item['qty'], unit_price=item['product'].price, line_total=item['line_total'])
        _send_order_received_email(order)
        request.session['cart'] = {}
        if table_number:
            request.session.pop('table_number', None)
        if payment_method == 'stripe' and settings.STRIPE_SECRET_KEY:
            return redirect('shop:stripe_checkout', order_id=order.id)
        messages.success(request, 'Commande créée. Une facture est disponible.')
        return redirect(order.get_absolute_url())
    pizza_qty = _pizza_qty(items)
    return render(request, 'shop/checkout.html', {
        'items': items, 'total': total, 'stripe_enabled': bool(settings.STRIPE_SECRET_KEY), 'loyalty_rewards': LoyaltyReward.objects.filter(is_active=True),
        'pizza_qty': pizza_qty, 'loyalty_remaining': max(0, 5 - pizza_qty),
        'loyalty_gift_eligible': pizza_qty >= 5, 'table_number': table_number,
    })

def create_checkout_session(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode='payment',
        customer_email=order.email,
        payment_method_types=['card'],
        line_items=[{'price_data': {'currency': 'eur', 'product_data': {'name': f'Commande {order.order_number}'}, 'unit_amount': int(order.total * 100)}, 'quantity': 1}],
        success_url=settings.SITE_URL + reverse('shop:payment_success', args=[order.order_number]),
        cancel_url=settings.SITE_URL + reverse('shop:invoice', args=[order.order_number]),
    )
    order.stripe_session_id = session.id
    order.save(update_fields=['stripe_session_id'])
    return redirect(session.url)

def payment_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    order.payment_status = 'paid'
    order.save(update_fields=['payment_status'])
    messages.success(request, 'Paiement par carte confirmé. Merci pour votre commande.')
    return redirect(order.get_absolute_url())

def invoice(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items'), order_number=order_number)
    return render(request, 'shop/invoice.html', {'order': order})


def _safe_next_url(request, fallback):
    next_url = request.POST.get('next') or request.GET.get('next') or fallback
    return next_url if next_url.startswith('/') else fallback


def _login_fallback(role):
    if role == 'kitchen':
        return reverse('shop:kitchen_app')
    if role == 'staff':
        return reverse('shop:staff_portal')
    return reverse('shop:owner_dashboard')


def app_home(request):
    return render(request, 'shop/app_home.html', {
        'kitchen_app': True,
        'meta_title': 'Application Pizza Vitti',
    })


def app_role(request, role):
    role_map = {
        'proprietaire': 'owner',
        'owner': 'owner',
        'cuisine': 'kitchen',
        'kitchen': 'kitchen',
        'staff': 'staff',
    }
    selected_role = role_map.get(role, 'owner')
    return redirect(f"{reverse('shop:app_login')}?role={selected_role}")


def app_login(request, default_role='owner'):
    selected_role = request.POST.get('role') or request.GET.get('role') or default_role
    if selected_role not in ['owner', 'kitchen', 'staff']:
        selected_role = 'owner'
    fallback = _login_fallback(selected_role)
    if selected_role == 'owner' and _session_or_staff(request, 'owner_access'):
        return redirect(_safe_next_url(request, fallback))
    if selected_role == 'kitchen' and (_session_or_staff(request, 'kitchen_access') or _session_or_staff(request, 'owner_access')):
        return redirect(_safe_next_url(request, fallback))
    if selected_role == 'staff' and request.session.get('staff_id'):
        return redirect(_safe_next_url(request, fallback))
    if request.method == 'POST':
        password = request.POST.get('password', '')
        if selected_role == 'owner' and _password_matches(password, settings.OWNER_DASHBOARD_PASSWORD):
            request.session['owner_access'] = True
            request.session['kitchen_access'] = True
            messages.success(request, 'Accès propriétaire activé.')
            return redirect(_safe_next_url(request, reverse('shop:owner_dashboard')))
        if selected_role == 'kitchen' and _password_matches(password, settings.KITCHEN_PASSWORD):
            request.session['kitchen_access'] = True
            messages.success(request, 'Accès cuisine activé.')
            return redirect(_safe_next_url(request, reverse('shop:kitchen_app')))
        if selected_role == 'staff':
            username = request.POST.get('username', '').strip()
            staff = StaffMember.objects.filter(username__iexact=username, is_active=True).first()
            if staff and staff.check_password(password):
                request.session['staff_id'] = staff.id
                messages.success(request, f'Bonjour {staff.name}.')
                return redirect(_safe_next_url(request, reverse('shop:staff_portal')))
        messages.error(request, 'Identifiant ou mot de passe incorrect.')
    return render(request, 'shop/app_login.html', {
        'next': request.GET.get('next', fallback),
        'selected_role': selected_role,
        'kitchen_app': True,
        'meta_title': 'Connexion application | Pizza Vitti',
    })


def kitchen_login(request):
    return app_login(request, 'kitchen')


def kitchen_logout(request):
    request.session.pop('kitchen_access', None)
    messages.success(request, 'Session cuisine fermée.')
    return redirect('shop:app_login')


def owner_login(request):
    return app_login(request, 'owner')


def owner_logout(request):
    request.session.pop('owner_access', None)
    messages.success(request, 'Session propriétaire fermée.')
    return redirect('shop:app_login')


def _report_stats(start, end=None):
    qs = Order.objects.filter(created_at__gte=start)
    if end:
        qs = qs.filter(created_at__lt=end)
    data = qs.aggregate(count=Count('id'), revenue=Sum('total'))
    return {'count': data['count'] or 0, 'revenue': data['revenue'] or Decimal('0.00')}


@owner_required
def owner_dashboard(request):
    today_start, now = _today_bounds()
    active_orders = Order.objects.filter(status__in=['received','preparing','ready'])
    today_orders = Order.objects.filter(created_at__gte=today_start)
    today_staff = StaffShift.objects.filter(check_in_at__date=timezone.localdate())
    stats = today_orders.aggregate(count=Count('id'), revenue=Sum('total'))
    most_ordered = (
        OrderItem.objects.filter(order__created_at__gte=today_start)
        .values('name')
        .annotate(quantity=Sum('quantity'))
        .order_by('-quantity')[:5]
    )
    return render(request, 'shop/owner_dashboard.html', {
        'orders_count': stats['count'] or 0,
        'revenue': stats['revenue'] or Decimal('0.00'),
        'active_orders_count': active_orders.count(),
        'staff_present_count': today_staff.exclude(status='checked_out').count(),
        'open_purchase_count': PurchaseOrder.objects.exclude(status__in=['received','cancelled']).count(),
        'recent_orders': Order.objects.prefetch_related('items').order_by('-created_at')[:8],
        'most_ordered': most_ordered,
        'kitchen_app': True,
        'meta_title': 'Dashboard propriétaire | Pizza Vitti',
    })


def _ensure_default_tables():
    if DiningTable.objects.exists():
        return
    defaults = []
    for idx in range(1, 13):
        col = (idx - 1) % 4
        row = (idx - 1) // 4
        defaults.append(DiningTable(label=str(idx), seats=2 + (idx % 3), x=10 + col * 24, y=14 + row * 28))
    DiningTable.objects.bulk_create(defaults)


@owner_required
def floor_plan(request):
    _ensure_default_tables()
    tables = list(DiningTable.objects.filter(is_active=True))
    active_orders = Order.objects.filter(status__in=['received','preparing','ready'], table_number__isnull=False).order_by('created_at')
    orders_by_table = {}
    for order in active_orders:
        if order.table_number:
            orders_by_table[str(order.table_number)] = order
    for table in tables:
        table.current_order = orders_by_table.get(str(table.label))
        table.public_url = request.build_absolute_uri(reverse('shop:table_menu', args=[table.label]))
    return render(request, 'shop/floor_plan.html', {
        'tables': tables,
        'kitchen_app': True,
        'meta_title': 'Plan de salle | Pizza Vitti',
    })


@owner_required
def purchase_orders(request):
    if request.method == 'POST':
        supplier = request.POST.get('supplier', '').strip()
        if supplier:
            PurchaseOrder.objects.create(
                supplier=supplier,
                reference=request.POST.get('reference', '').strip(),
                expected_date=request.POST.get('expected_date') or None,
                total=Decimal(request.POST.get('total') or '0'),
                status=request.POST.get('status') or 'draft',
                notes=request.POST.get('notes', '').strip(),
            )
            messages.success(request, 'Commande fournisseur ajoutée.')
            return redirect('shop:purchase_orders')
        messages.error(request, 'Ajoutez au moins le fournisseur.')
    return render(request, 'shop/purchase_orders.html', {
        'purchase_orders': PurchaseOrder.objects.all()[:50],
        'kitchen_app': True,
        'meta_title': 'Commandes fournisseurs | Pizza Vitti',
    })


@owner_required
def staff_manage(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role', '').strip() or 'Équipe'
        if name and username and password:
            staff, created = StaffMember.objects.get_or_create(username=username, defaults={'name': name, 'role': role})
            staff.name = name
            staff.role = role
            staff.temporary_password = password
            staff.is_active = True
            staff.save()
            messages.success(request, 'Employé ajouté.' if created else 'Employé mis à jour.')
            return redirect('shop:staff_manage')
        messages.error(request, 'Nom, utilisateur et mot de passe sont obligatoires.')
    staff_members = StaffMember.objects.prefetch_related('shifts')
    latest_shifts = {}
    for shift in StaffShift.objects.select_related('staff').order_by('-created_at')[:100]:
        latest_shifts.setdefault(shift.staff_id, shift)
    for staff in staff_members:
        staff.latest_shift = latest_shifts.get(staff.id)
    return render(request, 'shop/staff_manage.html', {
        'staff_members': staff_members,
        'kitchen_app': True,
        'meta_title': 'Équipe | Pizza Vitti',
    })


@owner_required
def staff_qr(request):
    login_url = request.build_absolute_uri(f"{reverse('shop:app_login')}?role=staff")
    return render(request, 'shop/staff_qr.html', {
        'login_url': login_url,
        'qr_url': f'https://api.qrserver.com/v1/create-qr-code/?size=320x320&data={quote(login_url)}',
        'kitchen_app': True,
        'meta_title': 'QR équipe | Pizza Vitti',
    })


@owner_required
def reports_dashboard(request):
    today_start, now = _today_bounds()
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    year_start = today_start.replace(month=1, day=1)
    reports = [
        ('Aujourd’hui', _report_stats(today_start)),
        ('Cette semaine', _report_stats(week_start)),
        ('Ce mois', _report_stats(month_start)),
        ('Cette année', _report_stats(year_start)),
    ]
    staff_shifts = StaffShift.objects.select_related('staff').filter(check_in_at__gte=week_start)[:60]
    return render(request, 'shop/reports_dashboard.html', {
        'reports': reports,
        'staff_shifts': staff_shifts,
        'kitchen_app': True,
        'meta_title': 'Rapports | Pizza Vitti',
    })


def staff_login(request):
    return app_login(request, 'staff')


def staff_logout(request):
    request.session.pop('staff_id', None)
    messages.success(request, 'Session équipe fermée.')
    return redirect(f"{reverse('shop:app_login')}?role=staff")


def _current_staff(request):
    staff_id = request.session.get('staff_id')
    if not staff_id:
        return None
    return StaffMember.objects.filter(id=staff_id, is_active=True).first()


def staff_portal(request):
    staff = _current_staff(request)
    if not staff:
        return redirect(f"{reverse('shop:app_login')}?role=staff")
    today = timezone.localdate()
    shift = StaffShift.objects.filter(staff=staff, check_in_at__date=today).order_by('-created_at').first()
    return render(request, 'shop/staff_portal.html', {
        'staff_member': staff,
        'shift': shift,
        'kitchen_app': True,
        'meta_title': 'Pointage équipe | Pizza Vitti',
    })


@require_POST
def staff_action(request):
    staff = _current_staff(request)
    if not staff:
        return redirect(f"{reverse('shop:app_login')}?role=staff")
    action = request.POST.get('action')
    now = timezone.now()
    today = timezone.localdate()
    shift = StaffShift.objects.filter(staff=staff, check_in_at__date=today).order_by('-created_at').first()
    if action == 'check_in':
        if not shift or shift.status == 'checked_out':
            StaffShift.objects.create(staff=staff, status='checked_in', check_in_at=now)
        else:
            shift.status = 'checked_in'
            shift.save(update_fields=['status','updated_at'])
        messages.success(request, 'Entrée enregistrée.')
    elif shift and action == 'break':
        shift.status = 'break'
        shift.break_started_at = now
        shift.save(update_fields=['status','break_started_at','updated_at'])
        messages.success(request, 'Pause démarrée.')
    elif shift and action == 'back':
        shift.status = 'checked_in'
        shift.break_ended_at = now
        shift.save(update_fields=['status','break_ended_at','updated_at'])
        messages.success(request, 'Retour de pause enregistré.')
    elif shift and action == 'check_out':
        shift.status = 'checked_out'
        shift.check_out_at = now
        shift.save(update_fields=['status','check_out_at','updated_at'])
        messages.success(request, 'Sortie enregistrée.')
    return redirect('shop:staff_portal')


@kitchen_required
def qr_tables(request):
    try:
        count = min(max(int(request.GET.get('count', 20)), 1), 80)
    except ValueError:
        count = 20
    base_url = request.build_absolute_uri(reverse('shop:home')).rstrip('/')
    tables = []
    for number in range(1, count + 1):
        url = request.build_absolute_uri(reverse('shop:table_menu', args=[number]))
        tables.append({'number': number, 'url': url})
    return render(request, 'shop/qr_tables.html', {
        'tables': tables,
        'base_url': base_url,
        'meta_title': 'QR codes tables | Pizza Vitti',
    })

@kitchen_required
def preparation_dashboard(request):
    active_statuses = ['received', 'preparing', 'ready']
    orders_qs = Order.objects.filter(status__in=active_statuses).prefetch_related('items').order_by('created_at')
    latest_order = orders_qs.order_by('-created_at').first()
    orders = list(orders_qs)
    for order in orders:
        order.whatsapp_received_url = _whatsapp_customer_url(order, 'received')
        order.whatsapp_ready_url = _whatsapp_customer_url(order, 'ready')
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'latest_order_key': latest_order.order_number if latest_order else '',
            'count': len(orders),
        })
    return render(request, 'shop/preparation_dashboard.html', {
        'orders': orders,
        'latest_order_key': latest_order.order_number if latest_order else '',
        'now': timezone.now(),
        'kitchen_app': True,
        'meta_title': 'Préparation commandes | Pizza Vitti',
    })

@kitchen_required
@require_POST
def update_order_status(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    status = request.POST.get('status')
    if status in dict(Order.STATUS):
        order.status = status
        order.save(update_fields=['status'])
        if status == 'ready':
            _send_order_ready_email(order)
        messages.success(request, f'Commande {order.order_number} mise à jour.')
    return redirect('shop:preparation_dashboard')

def track_order(request):
    order = None
    if request.method == 'POST':
        number = request.POST.get('order_number','').strip().upper()
        order = Order.objects.filter(order_number__iexact=number).first()
        if not order: messages.error(request, 'Aucune commande trouvée avec ce numéro.')
    return render(request, 'shop/track_order.html', {'order': order})

@require_POST
def report_order_issue(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    issue = request.POST.get('issue')
    if issue in ['not_received','refused']:
        order.status = issue
        order.delivery_issue_note = request.POST.get('delivery_issue_note','').strip()
        order.save(update_fields=['status','delivery_issue_note'])
        messages.success(request, 'Votre signalement a été enregistré. Nous vous contacterons rapidement.')
    return redirect(order.get_absolute_url())

def blog(request):
    posts = BlogPost.objects.filter(is_published=True)
    return render(request, 'shop/blog.html', {'posts': posts, 'meta_title': 'Blog | Pizza Vitti Bordeaux'})

def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    return render(request, 'shop/blog_detail.html', {'post': post, 'meta_title': post.meta_title or post.title, 'meta_description': post.meta_description or post.excerpt})

def contact(request):
    if request.method == 'POST':
        CustomerMessage.objects.create(name=request.POST.get('name',''), email=request.POST.get('email',''), phone=request.POST.get('phone',''), subject=request.POST.get('subject',''), message=request.POST.get('message',''))
        messages.success(request, 'Votre message a bien été envoyé à Pizza Vitti.')
        return redirect('shop:contact')
    return render(request, 'shop/contact.html')

@require_POST
def bot_reply(request):
    msg = request.POST.get('message','').lower()
    table_number = request.session.get('table_number', '').strip()
    if any(w in msg for w in ['table', 'qr', 'scan', 'scanner']):
        answer = f"Vous êtes sur la table {table_number}. Ajoutez vos plats au panier puis validez la commande." if table_number else "Scannez le QR code posé sur votre table : le site mémorise la table, puis vous pouvez commander depuis le menu."
    elif any(w in msg for w in ['menu', 'pizza', 'pasta', 'pâtes', 'raviol', 'boisson', 'dessert']):
        answer = "Le menu est organisé par familles : pizzas, pastas et ravioles, antipasti, menu bambino, douceurs et boissons. Cliquez sur une photo de catégorie pour ouvrir la page correspondante."
    elif any(w in msg for w in ['fidélité', 'fidelite', 'cadeau', '5 pizza', '5 pizzas']):
        answer = "Offre fidélité : chaque 5 pizzas commandées donnent droit à un cadeau. Pizza Vitti vous confirmera le cadeau selon disponibilité."
    elif any(w in msg for w in ['payer', 'visa', 'carte', 'paiement', 'stripe', 'cash', 'espèce', 'espece']):
        answer = "Vous pouvez payer par carte bancaire si Stripe est configuré, ou choisir le paiement au retrait / sur place selon l’organisation du restaurant."
    elif any(w in msg for w in ['réserver', 'reserver', 'reservation', 'réservation']):
        answer = "Pour réserver une table, utilisez la page Réserver et indiquez votre nom, téléphone, date, heure et nombre de personnes."
    elif any(w in msg for w in ['adresse', 'où', 'ou', 'localisation', 'maps', 'venir']):
        answer = "Pizza Vitti se trouve au 236 Rue d'Ornano, 33000 Bordeaux. Vous pouvez ouvrir Google Maps depuis la page contact ou le pied de page."
    elif any(w in msg for w in ['allerg', 'végétarien', 'vegetarien', 'sans gluten', 'halal']):
        answer = "Pour les allergènes ou demandes spéciales, ajoutez une note dans votre commande ou demandez confirmation au restaurant avant de valider."
    elif any(w in msg for w in ['suivi', 'statut', 'prête', 'prete', 'préparation', 'preparation']):
        answer = "Après commande, conservez votre numéro de commande. La facture affiche le statut : reçue, en préparation, prête ou servie."
    elif any(w in msg for w in ['avis', 'review', 'google', 'commentaire']):
        answer = "Après votre commande, vous pouvez laisser un avis depuis la page Avis. Vos commentaires Google aident beaucoup Pizza Vitti."
    elif any(w in msg for w in ['bonjour', 'salut', 'hello', 'hi']):
        answer = "Bonjour ! Je peux vous aider à choisir le menu, commander à table, comprendre la fidélité, réserver ou suivre une commande."
    else:
        answer = "Je peux vous aider pour le menu, les pizzas, les pastas, les boissons, la commande QR à table, la fidélité, la réservation, le paiement, les allergènes et les avis Google."
    return JsonResponse({'answer': answer})



def booking(request):
    if request.method == 'POST':
        Reservation.objects.create(
            name=request.POST.get('name','').strip(), email=request.POST.get('email','').strip(), phone=request.POST.get('phone','').strip(),
            date=request.POST.get('date'), time=request.POST.get('time'), guests=request.POST.get('guests') or 2, message=request.POST.get('message','').strip())
        messages.success(request, 'Votre demande de réservation a bien été envoyée. Pizza Vitti vous confirmera rapidement.')
        return redirect('shop:booking')
    return render(request, 'shop/booking.html', {'meta_title': 'Réservation | Pizza Vitti Bordeaux'})

def reviews(request):
    reviews = Review.objects.filter(is_published=True)
    return render(request, 'shop/reviews.html', {'reviews': reviews, 'meta_title': 'Avis clients | Pizza Vitti Bordeaux'})

def gallery(request):
    images = GalleryImage.objects.filter(is_active=True)
    return render(request, 'shop/gallery.html', {'images': images, 'meta_title': 'Galerie | Pizza Vitti Bordeaux'})

@require_POST
def newsletter(request):
    email = request.POST.get('email','').strip().lower()
    if email:
        NewsletterSubscriber.objects.get_or_create(email=email, defaults={'is_active': True})
        messages.success(request, 'Merci, votre inscription à la newsletter est enregistrée.')
    return redirect(request.POST.get('next') or 'shop:home')

def simple_page(request, title):
    return render(request, 'shop/simple.html', {'title': title})


def localized_dispatch(request, lang, page=None):
    if lang not in TRANSLATIONS:
        return redirect('shop:home')
    if lang == 'fr' and page == 'accueil':
        return redirect('/fr/')
    page = page or HOME_SLUGS.get(lang, '')
    dispatch = {'home': home, 'menu': boutique, 'booking': booking, 'reviews': reviews, 'gallery': gallery, 'blog': blog, 'contact': contact, 'cart': cart, 'checkout': checkout}
    for key, slugs in PAGE_SLUGS.items():
        if page == slugs.get(lang, ''):
            return dispatch.get(key, home)(request)
    return home(request)


@login_required
def customer_dashboard(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')[:8]
    pizza_count = _customer_pizza_count(request.user)
    favorites = Favorite.objects.filter(user=request.user).select_related('product', 'product__category')[:12]
    return render(request, 'shop/customer_dashboard.html', {
        'orders': orders,
        'pizza_count': pizza_count,
        'loyalty_remaining': max(0, 5 - (pizza_count % 5)) if pizza_count % 5 else 0,
        'pizza_progress': pizza_count % 5,
        'rewards_unlocked': pizza_count // 5,
        'favorites': favorites,
        'meta_title': 'Mon compte | Pizza Vitti',
    })

@login_required
def customer_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'shop/customer_orders.html', {'orders': orders, 'meta_title': 'Mes commandes | Pizza Vitti'})

@login_required
def customer_favorites(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('product', 'product__category')
    return render(request, 'shop/customer_favorites.html', {'favorites': favorites, 'meta_title': 'Mes favoris | Pizza Vitti'})

@login_required
@require_POST
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)
    fav, created = Favorite.objects.get_or_create(user=request.user, product=product)
    if created:
        messages.success(request, f'{product.name} ajouté à vos favoris.')
    else:
        fav.delete()
        messages.success(request, f'{product.name} retiré de vos favoris.')
    return redirect(request.POST.get('next') or product.get_absolute_url())

def robots_txt(request):
    sitemap_url = settings.SITE_URL.rstrip('/') + '/sitemap.xml'
    content = f"User-agent: *\nAllow: /\nSitemap: {sitemap_url}\n"
    return HttpResponse(content, content_type='text/plain')

def manifest_webmanifest(request):
    site_url = request.build_absolute_uri('/').rstrip('/')
    manifest = {
        'name': 'Pizza Vitti Application',
        'short_name': 'Vitti App',
        'description': 'Application Pizza Vitti pour le propriétaire, la cuisine et le pointage staff.',
        'start_url': '/app/',
        'scope': '/',
        'display': 'standalone',
        'orientation': 'any',
        'background_color': '#171923',
        'theme_color': '#171923',
        'categories': ['food', 'business', 'productivity'],
        'icons': [
            {'src': f'{site_url}/static/shop/img/pwa/icon-192.png', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any maskable'},
            {'src': f'{site_url}/static/shop/img/pwa/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'},
        ],
    }
    return HttpResponse(json.dumps(manifest), content_type='application/manifest+json')

def service_worker(request):
    content = """
const CACHE_NAME = 'pizza-vitti-kitchen-v2';
const STATIC_ASSETS = [
  '/static/shop/style.css',
  '/static/shop/app.js',
  '/static/shop/img/logo-vitti-header.png',
  '/static/shop/img/pwa/icon-192.png',
  '/static/shop/img/pwa/icon-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (request.mode === 'navigate' || request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(fetch(request));
    return;
  }
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }
  event.respondWith(fetch(request));
});
"""
    return HttpResponse(content.strip(), content_type='application/javascript')
