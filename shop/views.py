from decimal import Decimal
from uuid import uuid4
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, IntegerField
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
import stripe
from .models import BlogPost, Category, CustomerMessage, Order, OrderItem, Product, Reservation, Review, GalleryImage, NewsletterSubscriber, LoyaltyReward, Favorite, ProductTranslation, CategoryTranslation
from .translations import PAGE_SLUGS, HOME_SLUGS, TRANSLATIONS, get_lang_from_path


def _menu_category_order(qs):
    return qs.annotate(
        menu_priority=Case(
            When(name__iexact='Nos Pizza', then=0),
            When(name__iexact='Nos Pizzas', then=0),
            When(name__icontains='pizza', then=0),
            When(name__iexact='Nos Pasta', then=1),
            When(name__iexact='Nos Pastas', then=1),
            When(name__icontains='pasta', then=1),
            default=10,
            output_field=IntegerField(),
        )
    ).order_by('menu_priority', 'order', 'name')



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
    lang = get_lang_from_path(request.path)
    products = list(Product.objects.filter(is_available=True).select_related('category')[:180])
    posts = BlogPost.objects.filter(is_published=True)[:3]
    categories = list(_menu_category_order(Category.objects.filter(is_active=True).prefetch_related('products'))[:12])
    reviews = Review.objects.filter(is_published=True)[:6]
    gallery = GalleryImage.objects.filter(is_active=True)[:8]
    best_sellers = list(Product.objects.filter(is_available=True, is_best_seller=True).select_related('category')[:4])
    if not best_sellers:
        best_sellers = list(Product.objects.filter(is_available=True, category__name__icontains='pizza').select_related('category')[:4])
    pizza_of_month = Product.objects.filter(is_available=True, is_pizza_of_month=True).select_related('category').first()
    loyalty_reward = LoyaltyReward.objects.filter(is_active=True).first()
    _apply_menu_translations(products, categories, lang)
    _apply_menu_translations(best_sellers, [], lang)
    customer_pizza_count = _customer_pizza_count(request.user)
    favorite_product_ids = set()
    if request.user.is_authenticated:
        favorite_product_ids = set(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    return render(request, 'shop/home.html', {
        'products': products, 'posts': posts, 'categories': categories, 'reviews': reviews, 'gallery': gallery, 'best_sellers': best_sellers, 'pizza_of_month': pizza_of_month, 'loyalty_reward': loyalty_reward, 'customer_pizza_count': customer_pizza_count, 'customer_loyalty_remaining': max(0, 5 - (customer_pizza_count % 5)), 'favorite_product_ids': favorite_product_ids,
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
    return render(request, 'shop/boutique.html', {'page_obj': page_obj, 'query': query, 'favorite_product_ids': favorite_product_ids})

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
    return render(request, 'shop/boutique.html', {'page_obj': page_obj, 'category': cat, 'favorite_product_ids': favorite_product_ids})

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
    return redirect('shop:cart')

def checkout(request):
    items, total = _cart_items(request)
    if not items:
        messages.error(request, 'Votre panier est vide.')
        return redirect('shop:boutique')
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'stripe')
        order_type = request.POST.get('order_type', 'pickup')
        selected_reward = request.POST.get('selected_reward', '').strip() if _pizza_qty(items) >= 5 else ''
        order = Order.objects.create(
            order_number='PV-' + uuid4().hex[:8].upper(),
            user=request.user if request.user.is_authenticated else None,
            customer_type='particulier',
            customer_name=request.POST.get('name','').strip(), email=request.POST.get('email','').strip(),
            phone=request.POST.get('phone','').strip(), address=request.POST.get('address','').strip(), order_type=order_type, selected_reward=selected_reward, promo_code=request.POST.get('promo_code','').strip(),
            notes=(request.POST.get('notes','').strip() + ('\nOffre fidélité: cadeau à préparer: ' + (selected_reward or 'au choix client') if _pizza_qty(items) >= 5 else '')).strip(), total=total,
            payment_status='pending' if payment_method == 'stripe' else 'cash')
        for item in items:
            OrderItem.objects.create(order=order, product=item['product'], name=item['product'].name,
                quantity=item['qty'], unit_price=item['product'].price, line_total=item['line_total'])
        request.session['cart'] = {}
        if payment_method == 'stripe' and settings.STRIPE_SECRET_KEY:
            return redirect('shop:stripe_checkout', order_id=order.id)
        messages.success(request, 'Commande créée. Une facture est disponible.')
        return redirect(order.get_absolute_url())
    pizza_qty = _pizza_qty(items)
    return render(request, 'shop/checkout.html', {
        'items': items, 'total': total, 'stripe_enabled': bool(settings.STRIPE_SECRET_KEY), 'loyalty_rewards': LoyaltyReward.objects.filter(is_active=True),
        'pizza_qty': pizza_qty, 'loyalty_remaining': max(0, 5 - pizza_qty),
        'loyalty_gift_eligible': pizza_qty >= 5,
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
    if any(w in msg for w in ['payer', 'visa', 'carte', 'paiement']):
        answer = "Vous pouvez payer par carte bancaire Visa/Mastercard via Stripe si les clés Stripe sont configurées, ou choisir le paiement au retrait."
    elif any(w in msg for w in ['livraison', 'retrait', 'commande']):
        answer = "Après commande, vous recevez un numéro. Utilisez la page Suivi pour voir si la commande est reçue, en préparation, prête ou livrée."
    else:
        answer = "Bonjour ! Je peux vous aider pour le menu, les pizzas, les horaires, la commande, le retrait, la réservation et le paiement par carte."
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
