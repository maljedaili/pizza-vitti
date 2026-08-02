from decimal import Decimal
from datetime import date, datetime, timedelta
from functools import wraps
import json
import requests
from urllib.parse import quote
from uuid import uuid4
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, logout
from django.contrib.auth.hashers import check_password
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Case, When, IntegerField, Sum, Count, Prefetch
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import stripe
from .forms import CheckoutForm, ReservationForm
from .models import BlogPost, Category, CustomerMessage, Order, OrderItem, Product, Reservation, Review, GalleryImage, NewsletterSubscriber, LoyaltyReward, LoyaltyRedemption, Favorite, ProductTranslation, CategoryTranslation, DiningTable, StaffMember, StaffShift, PurchaseOrder, CameraLocation, SecurityCamera, PromoCode, SiteConfiguration
from .translations import PAGE_SLUGS, HOME_SLUGS, TRANSLATIONS, get_lang_from_path, localized_url, t_for


def _password_matches(raw_password, configured_password):
    return bool(raw_password) and raw_password == configured_password


def _owner_password_matches(raw_password):
    password_hash = getattr(settings, 'OWNER_DASHBOARD_PASSWORD_HASH', '')
    if password_hash:
        return bool(raw_password) and check_password(raw_password, password_hash)
    return _password_matches(raw_password, settings.OWNER_DASHBOARD_PASSWORD)


def _owner_username_matches(raw_username):
    return bool(raw_username) and raw_username == settings.OWNER_DASHBOARD_USERNAME


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
            When(name__iexact='Nos pâtes', then=1),
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
        'title': 'Nos pizzas',
        'eyebrow': 'Pizza',
        'summary': 'Toutes les pizzas maison avec les suppléments pour personnaliser votre commande.',
        'kind': 'is-pizza',
        'image': '/static/shop/img/hero/menu-pizza-vitti.jpg',
        'matches': ('pizza', 'suppl'),
    },
    {
        'slug': 'pastas',
        'title': 'Nos pâtes',
        'eyebrow': 'Pasta',
        'summary': 'Pastas italiennes, ravioles et recettes généreuses servies bien chaudes.',
        'kind': 'is-pasta',
        'image': '/static/shop/img/hero/menu-pasta.jpg',
        'matches': ('pasta', 'pâte', 'raviole'),
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
        'image': '/static/shop/img/hero/menu-bambino-pizza.jpg',
        'matches': ('bambino',),
    },
    {
        'slug': 'douceurs',
        'title': 'Nos douceurs',
        'eyebrow': 'Desserts',
        'summary': 'Tiramisu, panna cotta, glaces et desserts italiens.',
        'kind': 'is-dessert',
        'image': '/static/shop/img/hero/menu-tiramisu.jpg',
        'matches': ('douceur', 'dessert', 'glace'),
    },
    {
        'slug': 'boissons',
        'title': 'Boissons',
        'eyebrow': 'Bar',
        'summary': 'Softs, bières, vins, apéritifs, digestifs, cafés et thés.',
        'kind': 'is-drink',
        'image': '/static/shop/img/drinks/shirley-temple-cosmopolitan.jpg',
        'matches': ('aperitivo', 'digestif', 'birre', 'analcolici', 'caff', 'cafe', 'cappuccino', 'chocolat', 'the', 'vin'),
    },
]

DRINKS_GROUP_TRANSLATIONS = {
    'fr': {'title': 'Boissons', 'eyebrow': 'Bar italien', 'summary': 'Softs, bières, vins, apéritifs, digestifs, cafés et thés.'},
    'en': {'title': 'Drinks', 'eyebrow': 'Italian bar', 'summary': 'Soft drinks, beers, wines, aperitifs, digestifs, coffees and teas.'},
    'es': {'title': 'Bebidas', 'eyebrow': 'Bar italiano', 'summary': 'Refrescos, cervezas, vinos, aperitivos, digestivos, cafés y tés.'},
    'it': {'title': 'Bevande', 'eyebrow': 'Bar italiano', 'summary': 'Bibite, birre, vini, aperitivi, digestivi, caffè e tè.'},
    'pt': {'title': 'Bebidas', 'eyebrow': 'Bar italiano', 'summary': 'Refrigerantes, cervejas, vinhos, aperitivos, digestivos, cafés e chás.'},
    'nl': {'title': 'Dranken', 'eyebrow': 'Italiaanse bar', 'summary': 'Frisdranken, bier, wijn, aperitieven, digestieven, koffie en thee.'},
    'zh': {'title': '饮品', 'eyebrow': '意式酒吧', 'summary': '软饮、啤酒、葡萄酒、开胃酒、餐后酒、咖啡和茶。'},
    'ja': {'title': 'ドリンク', 'eyebrow': 'イタリアンバー', 'summary': 'ソフトドリンク、ビール、ワイン、食前酒、食後酒、コーヒー、紅茶。'},
    'ar': {'title': 'المشروبات', 'eyebrow': 'بار إيطالي', 'summary': 'مشروبات غازية وبيرة ونبيذ ومقبلات ومشروبات هاضمة وقهوة وشاي.'},
}

MENU_GROUP_TRANSLATIONS = {
    'en': {
        'pizzas': {'title': 'Our pizzas', 'eyebrow': 'Pizza', 'summary': 'House-made pizzas with extras to personalise your order.'},
        'pastas': {'title': 'Our pasta', 'eyebrow': 'Pasta', 'summary': 'Italian pasta, ravioli and generous recipes served piping hot.'},
        'antipasti': {'title': 'Starters & antipasti', 'eyebrow': 'To share', 'summary': 'Starters, antipasti, bruschetta and salads to begin or share.'},
        'bambino': {'title': 'Kids menu', 'eyebrow': 'Children', 'summary': 'A simple and delicious menu created for younger guests.'},
        'douceurs': {'title': 'Our desserts', 'eyebrow': 'Desserts', 'summary': 'Tiramisu, panna cotta, ice cream and Italian desserts.'},
    },
    'es': {
        'pizzas': {'title': 'Nuestras pizzas', 'eyebrow': 'Pizza', 'summary': 'Pizzas caseras con extras para personalizar tu pedido.'},
        'pastas': {'title': 'Nuestras pastas', 'eyebrow': 'Pasta', 'summary': 'Pasta italiana, raviolis y recetas generosas servidas bien calientes.'},
        'antipasti': {'title': 'Entrantes y antipasti', 'eyebrow': 'Para compartir', 'summary': 'Entrantes, antipasti, bruschettas y ensaladas para empezar o compartir.'},
        'bambino': {'title': 'Menú infantil', 'eyebrow': 'Niños', 'summary': 'Un menú sencillo y sabroso pensado para los más pequeños.'},
        'douceurs': {'title': 'Nuestros postres', 'eyebrow': 'Postres', 'summary': 'Tiramisú, panna cotta, helados y postres italianos.'},
    },
    'it': {
        'pizzas': {'title': 'Le nostre pizze', 'eyebrow': 'Pizza', 'summary': 'Pizze fatte in casa con aggiunte per personalizzare l’ordine.'},
        'pastas': {'title': 'La nostra pasta', 'eyebrow': 'Pasta', 'summary': 'Pasta italiana, ravioli e ricette generose servite ben calde.'},
        'antipasti': {'title': 'Antipasti', 'eyebrow': 'Da condividere', 'summary': 'Antipasti, bruschette e insalate per iniziare o condividere.'},
        'bambino': {'title': 'Menu bambino', 'eyebrow': 'Bambini', 'summary': 'Un menu semplice e gustoso pensato per i più piccoli.'},
        'douceurs': {'title': 'I nostri dolci', 'eyebrow': 'Dolci', 'summary': 'Tiramisù, panna cotta, gelati e dessert italiani.'},
    },
    'pt': {
        'pizzas': {'title': 'As nossas pizzas', 'eyebrow': 'Pizza', 'summary': 'Pizzas artesanais com extras para personalizar o pedido.'},
        'pastas': {'title': 'As nossas massas', 'eyebrow': 'Pasta', 'summary': 'Massas italianas, ravioli e receitas generosas servidas bem quentes.'},
        'antipasti': {'title': 'Entradas e antipasti', 'eyebrow': 'Para partilhar', 'summary': 'Entradas, antipasti, bruschettas e saladas para começar ou partilhar.'},
        'bambino': {'title': 'Menu infantil', 'eyebrow': 'Crianças', 'summary': 'Um menu simples e saboroso pensado para os mais novos.'},
        'douceurs': {'title': 'As nossas sobremesas', 'eyebrow': 'Sobremesas', 'summary': 'Tiramisù, panna cotta, gelados e sobremesas italianas.'},
    },
    'nl': {
        'pizzas': {'title': 'Onze pizza’s', 'eyebrow': 'Pizza', 'summary': 'Huisgemaakte pizza’s met extra’s om je bestelling aan te passen.'},
        'pastas': {'title': 'Onze pasta', 'eyebrow': 'Pasta', 'summary': 'Italiaanse pasta, ravioli en royale gerechten, warm geserveerd.'},
        'antipasti': {'title': 'Voorgerechten & antipasti', 'eyebrow': 'Om te delen', 'summary': 'Voorgerechten, antipasti, bruschetta en salades om te starten of delen.'},
        'bambino': {'title': 'Kindermenu', 'eyebrow': 'Kinderen', 'summary': 'Een eenvoudig en lekker menu voor onze jongste gasten.'},
        'douceurs': {'title': 'Onze desserts', 'eyebrow': 'Desserts', 'summary': 'Tiramisu, panna cotta, ijs en Italiaanse desserts.'},
    },
    'zh': {
        'pizzas': {'title': '我们的披萨', 'eyebrow': '披萨', 'summary': '手工披萨，可选配料定制您的订单。'},
        'pastas': {'title': '我们的意面', 'eyebrow': '意面', 'summary': '热腾腾的意大利面、意式饺子和丰盛菜品。'},
        'antipasti': {'title': '前菜与开胃菜', 'eyebrow': '分享', 'summary': '前菜、意式开胃菜、烤面包和沙拉，适合开胃或分享。'},
        'bambino': {'title': '儿童菜单', 'eyebrow': '儿童', 'summary': '为小客人准备的简单美味菜单。'},
        'douceurs': {'title': '我们的甜点', 'eyebrow': '甜点', 'summary': '提拉米苏、奶冻、冰淇淋和意大利甜点。'},
    },
    'ja': {
        'pizzas': {'title': 'ピザ', 'eyebrow': 'ピザ', 'summary': '手作りピザにトッピングを追加してカスタマイズできます。'},
        'pastas': {'title': 'パスタ', 'eyebrow': 'パスタ', 'summary': '熱々のイタリアンパスタ、ラビオリ、ボリュームある料理。'},
        'antipasti': {'title': '前菜＆アンティパスト', 'eyebrow': 'シェア', 'summary': '前菜、ブルスケッタ、サラダをスターターやシェアに。'},
        'bambino': {'title': 'キッズメニュー', 'eyebrow': 'お子様', 'summary': 'お子様向けのシンプルでおいしいメニュー。'},
        'douceurs': {'title': 'デザート', 'eyebrow': 'デザート', 'summary': 'ティラミス、パンナコッタ、アイス、イタリアンスイーツ。'},
    },
    'ar': {
        'pizzas': {'title': 'البيتزا', 'eyebrow': 'بيتزا', 'summary': 'بيتزا منزلية مع إضافات لتخصيص طلبكم.'},
        'pastas': {'title': 'المعكرونة', 'eyebrow': 'باستا', 'summary': 'معكرونة إيطالية ورافيولي ووصفات سخية تُقدّم ساخنة.'},
        'antipasti': {'title': 'المقبلات', 'eyebrow': 'للمشاركة', 'summary': 'مقبلات وبروشيتا وسلطات للبداية أو المشاركة.'},
        'bambino': {'title': 'قائمة الأطفال', 'eyebrow': 'أطفال', 'summary': 'قائمة بسيطة ولذيذة مخصّصة للصغار.'},
        'douceurs': {'title': 'الحلويات', 'eyebrow': 'حلويات', 'summary': 'تيراميسو وبانا كوتا وآيس كريم وحلويات إيطالية.'},
    },
}

DRINK_CATEGORY_ORDER = [
    'caffe-the', 'cafe-allonge', 'cafe-double', 'cappuccino', 'chocolat-chaud',
    'thes-et-infusions', 'carte-des-vins-rouges', 'carte-des-vins-blancs',
    'carte-des-vins-roses', 'carte-des-vins-petillants', 'aperitivo',
    'vins-deliveroo', 'analcolici', 'digestifs',
]

ALCOHOL_CATEGORY_SLUGS = {
    'carte-des-vins-rouges', 'carte-des-vins-blancs', 'carte-des-vins-roses',
    'carte-des-vins-petillants', 'aperitivo', 'vins-deliveroo', 'birre', 'digestifs',
}


def _requires_age_verification(product):
    category_slug = product.category.slug if product.category else ''
    if category_slug in ALCOHOL_CATEGORY_SLUGS:
        return True
    product_text = f'{product.name} {product.badge}'.lower()
    return category_slug == 'analcolici' and any(
        word in product_text for word in ('bière', 'beer', 'birra', 'peroni', 'moretti')
    )

MENU_GROUP_IMAGE_FIELDS = {
    'pizzas': 'pizzas_banner_image',
    'pastas': 'pastas_banner_image',
    'antipasti': 'antipasti_banner_image',
    'bambino': 'bambino_banner_image',
    'douceurs': 'desserts_banner_image',
    'boissons': 'drinks_banner_image',
}


def _apply_menu_group_image(item, site_config):
    image_field = getattr(site_config, MENU_GROUP_IMAGE_FIELDS[item['slug']], None)
    if image_field:
        item['image'] = image_field.url
        item['uploaded_image_url'] = image_field.url


def _category_key(category):
    return f'{category.name} {category.slug}'.lower()


def _categories_for_group(group):
    categories = list(_menu_category_order(Category.objects.filter(is_active=True)))
    return [category for category in categories if any(match in _category_key(category) for match in group['matches'])]


def _menu_groups(lang='fr'):
    groups = []
    site_config = SiteConfiguration.load()
    for group in MENU_GROUPS:
        categories = _categories_for_group(group)
        if not categories:
            continue
        item = group.copy()
        if group['slug'] == 'boissons':
            item.update(DRINKS_GROUP_TRANSLATIONS.get(lang, DRINKS_GROUP_TRANSLATIONS['fr']))
        elif group['slug'] in MENU_GROUP_TRANSLATIONS.get(lang, {}):
            item.update(MENU_GROUP_TRANSLATIONS[lang][group['slug']])
        _apply_menu_group_image(item, site_config)
        item['url'] = reverse('shop:localized_menu_group', args=[lang, group['slug']])
        item['count'] = sum(category.products.filter(is_available=True).count() for category in categories)
        groups.append(item)
    return groups


def _menu_group_by_slug(slug, lang='fr'):
    site_config = SiteConfiguration.load()
    for group in MENU_GROUPS:
        if group['slug'] == slug:
            item = group.copy()
            if slug == 'boissons':
                item.update(DRINKS_GROUP_TRANSLATIONS.get(lang, DRINKS_GROUP_TRANSLATIONS['fr']))
            elif slug in MENU_GROUP_TRANSLATIONS.get(lang, {}):
                item.update(MENU_GROUP_TRANSLATIONS[lang][slug])
            _apply_menu_group_image(item, site_config)
            return item
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


def _active_loyalty_reward():
    if not settings.LOYALTY_ENABLED:
        return None
    return LoyaltyReward.objects.filter(is_active=True).order_by('pizzas_required', 'name').first()


def _loyalty_status(user, additional_pizzas=0):
    reward = _active_loyalty_reward()
    pizzas_required = max(1, reward.pizzas_required if reward else 5)
    pizza_count = _customer_pizza_count(user)
    projected_pizzas = pizza_count + max(0, additional_pizzas)
    active_redemptions = LoyaltyRedemption.objects.none()
    if user.is_authenticated:
        active_redemptions = LoyaltyRedemption.objects.filter(user=user).exclude(
            order__status__in=['cancelled', 'refunded'],
        )
    redeemed_milestones = set(active_redemptions.values_list('milestone', flat=True))
    earned_milestones = list(range(pizzas_required, projected_pizzas + 1, pizzas_required))
    available_milestones = [
        milestone for milestone in earned_milestones
        if milestone not in redeemed_milestones
    ]
    progress = projected_pizzas % pizzas_required
    remaining = pizzas_required - progress
    if available_milestones:
        remaining = 0
    return {
        'reward': reward,
        'pizzas_required': pizzas_required,
        'pizza_count': pizza_count,
        'projected_pizzas': projected_pizzas,
        'progress': progress,
        'progress_percent': round((progress / pizzas_required) * 100),
        'remaining': remaining,
        'available_milestones': available_milestones,
        'available_rewards': len(available_milestones),
        'redeemed_rewards': active_redemptions.count(),
        'earned_rewards': projected_pizzas // pizzas_required,
    }


def _cart_items(request):
    cart = request.session.get('cart', {})
    products = Product.objects.filter(id__in=cart.keys()).select_related('category')
    items, total = [], Decimal('0.00')
    for p in products:
        if not p.is_orderable:
            continue
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

def root_redirect(request):
    return HttpResponsePermanentRedirect(localized_url('home', 'fr'))


def home(request):
    reviews = Review.objects.filter(is_published=True).exclude(source_url='')[:6]
    gallery = GalleryImage.objects.filter(is_active=True).exclude(image='').exclude(image__isnull=True)[:6]
    lang = get_lang_from_path(request.path)
    copy = t_for(lang)
    menu_groups = _menu_groups(lang)
    favorite_product_ids = set()
    if request.user.is_authenticated:
        favorite_product_ids = set(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    return render(request, 'shop/home.html', {
        'menu_groups': menu_groups,
        'reviews': reviews,
        'gallery': gallery,
        'favorite_product_ids': favorite_product_ids,
        'hide_review_prompt': True,
        'meta_title': copy['home_meta_title'],
        'meta_description': copy['home_meta_description'],
    })

def about(request):
    return HttpResponsePermanentRedirect(localized_url('home', 'fr'))

def faq(request):
    return render(request, 'shop/faq.html', {'meta_title': "FAQ | Commandes Pizza Vitti"})

def boutique(request):
    qs = Product.objects.select_related('category')
    query = request.GET.get('q','').strip()
    if query:
        qs = qs.filter(Q(name__icontains=query)|Q(description__icontains=query)|Q(category__name__icontains=query))
    paginator = Paginator(qs, 120)
    page_obj = paginator.get_page(request.GET.get('page'))
    lang = get_lang_from_path(request.path)
    copy = t_for(lang)
    _apply_menu_translations(list(page_obj.object_list), [], lang)
    favorite_product_ids = set()
    if request.user.is_authenticated:
        favorite_product_ids = set(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    return render(request, 'shop/boutique.html', {
        'page_obj': page_obj,
        'query': query,
        'favorite_product_ids': favorite_product_ids,
        'menu_groups': _menu_groups(lang),
        'meta_title': copy['menu_meta_title'],
        'meta_description': copy['menu_meta_description'],
    })

def category(request, slug):
    cat = get_object_or_404(Category, slug=slug, is_active=True)
    qs = cat.products.all()
    paginator = Paginator(qs, 120)
    page_obj = paginator.get_page(request.GET.get('page'))
    lang = get_lang_from_path(request.path)
    _apply_menu_translations(list(page_obj.object_list), [cat], lang)
    favorite_product_ids = set()
    if request.user.is_authenticated:
        favorite_product_ids = set(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    return render(request, 'shop/boutique.html', {'page_obj': page_obj, 'category': cat, 'favorite_product_ids': favorite_product_ids, 'menu_groups': _menu_groups(lang)})

def menu_group(request, group, lang=None):
    lang = lang or get_lang_from_path(request.path)
    menu_group_data = _menu_group_by_slug(group, lang)
    if not menu_group_data:
        return redirect('shop:boutique')
    categories = [
        category for category in _categories_for_group(menu_group_data)
        if 'suppl' not in _category_key(category)
    ]
    if group == 'boissons':
        drink_order = {slug: index for index, slug in enumerate(DRINK_CATEGORY_ORDER)}
        categories.sort(key=lambda category: drink_order.get(category.slug, 999))
    products = list(Product.objects.filter(category__in=categories).select_related('category'))
    _apply_menu_translations(products, categories, lang)
    for product in products:
        product.requires_age_verification = _requires_age_verification(product)
        if group == 'boissons' and not product.image and product.category.static_image_path:
            product.external_image = product.category.static_image_path
    sections = []
    for category in categories:
        section_products = [product for product in products if product.category_id == category.id]
        if section_products:
            sections.append({'category': category, 'products': section_products})
    favorite_product_ids = set()
    if request.user.is_authenticated:
        favorite_product_ids = set(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    drinks_copy = {
        'fr': ('BAR ITALIEN · CAFÉS · VINS', 'Boissons & Carte des vins', 'Cafés italiens, boissons fraîches, apéritifs et vins soigneusement sélectionnés pour accompagner votre repas.', 'Découvrir la carte', 'Voir les vins', 'Navigation des boissons'),
        'en': ('ITALIAN BAR · COFFEE · WINE', 'Drinks & Wine List', 'Italian coffees, refreshing drinks, aperitifs and carefully selected wines to accompany your meal.', 'Explore the menu', 'View wines', 'Drinks navigation'),
        'es': ('BAR ITALIANO · CAFÉS · VINOS', 'Bebidas y Carta de vinos', 'Cafés italianos, bebidas frescas, aperitivos y vinos cuidadosamente seleccionados para acompañar su comida.', 'Descubrir la carta', 'Ver los vinos', 'Navegación de bebidas'),
        'it': ('BAR ITALIANO · CAFFÈ · VINI', 'Bevande e Carta dei vini', 'Caffè italiani, bevande fresche, aperitivi e vini selezionati con cura per accompagnare il pasto.', 'Scopri il menu', 'Vedi i vini', 'Navigazione bevande'),
        'pt': ('BAR ITALIANO · CAFÉS · VINHOS', 'Bebidas e Carta de vinhos', 'Cafés italianos, bebidas frescas, aperitivos e vinhos cuidadosamente selecionados para acompanhar a refeição.', 'Descobrir o menu', 'Ver vinhos', 'Navegação de bebidas'),
        'nl': ('ITALIAANSE BAR · KOFFIE · WIJN', 'Dranken & Wijnkaart', 'Italiaanse koffie, frisse dranken, aperitieven en zorgvuldig geselecteerde wijnen voor bij uw maaltijd.', 'Ontdek de kaart', 'Bekijk wijnen', 'Dranknavigatie'),
        'zh': ('意式酒吧 · 咖啡 · 葡萄酒', '饮品与葡萄酒单', '意式咖啡、清爽饮品、开胃酒和精心挑选的葡萄酒，为您的餐点增添风味。', '浏览饮品单', '查看葡萄酒', '饮品导航'),
        'ja': ('イタリアンバー · コーヒー · ワイン', 'ドリンク＆ワインリスト', 'イタリアンコーヒー、爽やかなドリンク、食前酒、厳選ワインをお食事とともに。', 'メニューを見る', 'ワインを見る', 'ドリンクナビゲーション'),
        'ar': ('بار إيطالي · قهوة · نبيذ', 'المشروبات وقائمة النبيذ', 'قهوة إيطالية ومشروبات منعشة ومقبلات ونبيذ مختار بعناية لمرافقة وجبتكم.', 'اكتشف القائمة', 'عرض النبيذ', 'التنقل بين المشروبات'),
    }
    copy = drinks_copy.get(lang, drinks_copy['fr'])
    drinks_structured_data = ''
    if group == 'boissons':
        page_url = request.build_absolute_uri()
        menu_url = request.build_absolute_uri(reverse('shop:localized_page', args=[lang, 'menu']))
        drinks_structured_data = json.dumps({
            '@context': 'https://schema.org',
            '@graph': [
                {
                    '@type': 'BreadcrumbList',
                    'itemListElement': [
                        {'@type': 'ListItem', 'position': 1, 'name': 'Pizza Vitti', 'item': request.build_absolute_uri(f'/{lang}/')},
                        {'@type': 'ListItem', 'position': 2, 'name': 'Menu', 'item': menu_url},
                        {'@type': 'ListItem', 'position': 3, 'name': copy[1], 'item': page_url},
                    ],
                },
                {
                    '@type': 'Menu',
                    'name': copy[1],
                    'description': copy[2],
                    'url': page_url,
                    'hasMenuSection': [
                        {
                            '@type': 'MenuSection',
                            'name': getattr(section['category'], 'translated_name', section['category'].name),
                            'hasMenuItem': [
                                {
                                    '@type': 'MenuItem',
                                    'name': getattr(product, 'translated_name', product.name),
                                    'description': getattr(product, 'translated_description', product.description),
                                    'offers': {
                                        '@type': 'Offer',
                                        'price': str(product.price),
                                        'priceCurrency': 'EUR',
                                        'availability': 'https://schema.org/InStock',
                                    },
                                }
                                for product in section['products']
                            ],
                        }
                        for section in sections
                    ],
                },
            ],
        }, ensure_ascii=False)
    return render(request, 'shop/boutique.html', {
        'menu_group': menu_group_data,
        'menu_groups': _menu_groups(lang),
        'group_sections': sections,
        'group_products': products,
        'favorite_product_ids': favorite_product_ids,
        'meta_title': f"{menu_group_data['title']} | Pizza Vitti Bordeaux",
        'meta_description': menu_group_data['summary'],
        'is_drinks_page': group == 'boissons',
        'drinks_copy': {
            'eyebrow': copy[0], 'title': copy[1], 'subtitle': copy[2],
            'primary': copy[3], 'secondary': copy[4], 'nav_label': copy[5],
        },
        'meta_title': 'Boissons, cafés et vins italiens | Pizza Vitti Bordeaux' if group == 'boissons' else f"{menu_group_data['title']} | Pizza Vitti Bordeaux",
        'meta_description': 'Découvrez les cafés italiens, boissons fraîches, apéritifs, digestifs et la carte des vins de Pizza Vitti à Bordeaux.' if group == 'boissons' else menu_group_data['summary'],
        'meta_image': '/static/shop/img/drinks/shirley-temple-cosmopolitan.jpg' if group == 'boissons' else '',
        'drinks_structured_data': drinks_structured_data,
        'has_age_restricted_products': any(product.requires_age_verification for product in products),
    })

def product_detail(request, slug, lang=None):
    product = get_object_or_404(Product, slug=slug)
    lang = lang if lang in TRANSLATIONS else get_lang_from_path(request.path)
    _apply_menu_translations([product], [product.category] if product.category else [], lang)
    product.requires_age_verification = _requires_age_verification(product)
    favorite_product_ids = set()
    if request.user.is_authenticated:
        favorite_product_ids = set(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    supplements = list(Product.objects.filter(
        is_available=True,
        category__name__icontains='suppl',
    ).select_related('category')) if product.category and 'pizza' in _category_key(product.category) and 'suppl' not in _category_key(product.category) else []
    _apply_menu_translations(supplements, list({item.category for item in supplements if item.category}), lang)
    translated_name = getattr(product, 'translated_name', product.name)
    translated_description = getattr(product, 'translated_description', product.description)
    translated_category = getattr(product, 'translated_category_name', product.category.name if product.category else 'Menu')
    product_url = request.build_absolute_uri(
        reverse('shop:localized_product_detail', args=[lang, product.slug])
    )
    image_url = request.build_absolute_uri(product.display_image) if product.display_image else ''
    availability = (
        'https://schema.org/InStock' if product.is_orderable
        else 'https://schema.org/PreOrder' if product.availability_status == 'scheduled'
        else 'https://schema.org/OutOfStock'
    )
    page_structured_data = json.dumps({
        '@context': 'https://schema.org',
        '@graph': [
            {
                '@type': 'BreadcrumbList',
                'itemListElement': [
                    {'@type': 'ListItem', 'position': 1, 'name': 'Pizza Vitti', 'item': request.build_absolute_uri(localized_url('home', lang))},
                    {'@type': 'ListItem', 'position': 2, 'name': t_for(lang)['menu'], 'item': request.build_absolute_uri(localized_url('menu', lang))},
                    {'@type': 'ListItem', 'position': 3, 'name': translated_name, 'item': product_url},
                ],
            },
            {
                '@type': 'MenuItem',
                'name': translated_name,
                'description': translated_description,
                'image': image_url,
                'url': product_url,
                'menuAddOn': translated_category,
                'offers': {
                    '@type': 'Offer',
                    'price': str(product.price),
                    'priceCurrency': 'EUR',
                    'availability': availability,
                    'url': product_url,
                    'seller': {'@type': 'Restaurant', 'name': 'Pizza Vitti'},
                },
            },
        ],
    }, ensure_ascii=False)
    return render(request, 'shop/product_detail.html', {'product': product, 'supplements': supplements, 'favorite_product_ids': favorite_product_ids,
        'has_age_restricted_products': product.requires_age_verification,
        'meta_title': product.meta_title or f'{translated_name} | Pizza Vitti',
        'meta_description': product.meta_description or translated_description[:155],
        'meta_type': 'product',
        'meta_image_absolute': image_url,
        'meta_image_alt': translated_name,
        'page_structured_data': page_structured_data})


def legacy_boutique_redirect(request):
    return HttpResponsePermanentRedirect(reverse('shop:localized_page', args=['fr', 'menu']))


def legacy_menu_group_redirect(request, group):
    return HttpResponsePermanentRedirect(reverse('shop:localized_menu_group', args=['fr', group]))

def table_menu(request, table):
    table_number = ''.join(ch for ch in str(table) if ch.isalnum() or ch in '-_')[:20]
    if table_number:
        request.session['table_number'] = table_number
        messages.success(request, f'Table {table_number} sélectionnée. Choisissez vos plats, puis validez votre commande.')
    return redirect('shop:boutique')

@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product.objects.select_related('category'), id=product_id)
    next_path = request.POST.get('next', '')
    lang = get_lang_from_path(next_path)
    copy = t_for(lang)
    if not product.is_orderable:
        messages.error(request, copy['product_unavailable'])
        return redirect(_safe_next_url(request, localized_url('menu', lang)))
    if _requires_age_verification(product):
        confirmed = request.POST.get('age_confirmed') == '1' or request.session.get('alcohol_age_verified') is True
        if not confirmed:
            messages.error(request, copy['age_required_error'])
            return redirect(_safe_next_url(request, localized_url('menu', lang)))
        request.session['alcohol_age_verified'] = True
    cart = request.session.get('cart', {})
    try:
        qty = int(request.POST.get('qty', 1))
    except (TypeError, ValueError):
        qty = 1
    qty = min(20, max(1, qty))
    cart[str(product_id)] = min(20, int(cart.get(str(product_id), 0)) + qty)
    supplement_ids = request.POST.getlist('supplements')
    if supplement_ids and product.category and 'pizza' in _category_key(product.category):
        supplements = Product.objects.filter(
            id__in=supplement_ids,
            is_available=True,
            category__name__icontains='suppl',
        )
        for supplement in supplements:
            cart[str(supplement.id)] = min(20, int(cart.get(str(supplement.id), 0)) + qty)
    request.session['cart'] = cart
    messages.success(request, copy['item_added'])
    return redirect(_safe_next_url(request, localized_url('cart', lang)))

def cart(request):
    items, total = _cart_items(request)
    pizza_qty = _pizza_qty(items)
    loyalty = _loyalty_status(request.user, pizza_qty)
    guest_reward_count = pizza_qty // loyalty['pizzas_required'] if loyalty['reward'] else 0
    return render(request, 'shop/cart.html', {
        'items': items, 'total': total, 'pizza_qty': pizza_qty,
        'loyalty': loyalty,
        'loyalty_remaining': loyalty['remaining'],
        'loyalty_gift_eligible': bool(loyalty['available_rewards'] if request.user.is_authenticated else guest_reward_count),
        'loyalty_account_required': not request.user.is_authenticated,
        'table_number': request.session.get('table_number', '').strip(),
    })

@require_POST
def update_cart(request):
    next_path = request.POST.get('next', '')
    lang = get_lang_from_path(next_path)
    cart = {}
    for key, val in request.POST.items():
        if key.startswith('qty_'):
            try: qty = int(val)
            except ValueError: qty = 0
            if qty > 0: cart[key[4:]] = qty
    request.session['cart'] = cart
    messages.success(request, t_for(lang)['cart_updated'])
    return redirect(_safe_next_url(request, localized_url('cart', lang)))

@require_POST
def remove_from_cart(request, product_id):
    next_path = request.POST.get('next', '')
    lang = get_lang_from_path(next_path)
    cart = request.session.get('cart', {})
    cart.pop(str(product_id), None)
    request.session['cart'] = cart
    messages.success(request, t_for(lang)['item_removed'])
    return redirect(_safe_next_url(request, localized_url('cart', lang)))

def checkout(request):
    lang = get_lang_from_path(request.path)
    checkout_copy = t_for(lang)
    items, total = _cart_items(request)
    if not items:
        messages.error(request, checkout_copy['empty_cart'])
        return redirect(localized_url('menu', lang))
    table_number = request.session.get('table_number', '').strip()
    pizza_qty = _pizza_qty(items)
    loyalty = _loyalty_status(request.user, pizza_qty)
    guest_reward_count = pizza_qty // loyalty['pizzas_required'] if loyalty['reward'] else 0
    reward_count = loyalty['available_rewards'] if request.user.is_authenticated else guest_reward_count
    checkout_name = request.user.get_full_name().strip() if request.user.is_authenticated else ''
    checkout_email = request.user.email if request.user.is_authenticated else ''
    initial = {'name': checkout_name, 'email': checkout_email}
    form = CheckoutForm(request.POST or None, initial=initial)
    checkout_labels = {
        'name': checkout_copy['name'], 'email': checkout_copy['email'],
        'phone': checkout_copy['phone'],
        'collection_slot': f"{checkout_copy['date']} · {checkout_copy['time']}",
        'notes': checkout_copy['notes'], 'payment_method': checkout_copy['payment'],
        'accepted_terms': checkout_copy['order_terms'],
    }
    for field_name, label in checkout_labels.items():
        form.fields[field_name].label = label
    if not form.has_available_slots:
        form.fields['collection_slot'].choices = [('', checkout_copy['no_slots'])]
    form.fields['payment_method'].choices = [
        (value, checkout_copy['card_payment'] if value == 'stripe' else checkout_copy['pay_pickup'])
        for value, _label in form.fields['payment_method'].choices
    ]
    discount = Decimal('0.00')
    promo = None
    if request.method == 'POST':
        submitted_token = request.POST.get('checkout_token', '')
        session_token = request.session.get('checkout_token', '')
        if not submitted_token or submitted_token != session_token:
            form.add_error(None, 'Cette commande a déjà été envoyée ou la page a expiré. Vérifiez votre panier.')
        promo_code = request.POST.get('promo_code', '').strip().upper()
        if promo_code:
            promo = PromoCode.objects.filter(code__iexact=promo_code, is_active=True).first()
            if promo:
                discount = (total * Decimal(promo.discount_percent) / Decimal('100')).quantize(Decimal('0.01'))
            else:
                form.add_error('promo_code', 'Ce code promotionnel n’est pas valide.')
    final_total = max(Decimal('0.00'), total - discount)
    if request.method == 'POST' and form.is_valid():
        payment_method = form.cleaned_data['payment_method']
        order_type = 'dine_in' if table_number else 'pickup'
        collection_date, collection_time = form.cleaned_data['collection_slot']
        loyalty_reward = loyalty['reward'] if reward_count else None
        selected_reward = ''
        if loyalty_reward:
            selected_reward = loyalty_reward.get_reward_type_display()
            if reward_count > 1:
                selected_reward = f'{reward_count} × {selected_reward}'
        loyalty_note = f'{reward_count} cadeau(x) fidélité à préparer.' if reward_count else ''
        with transaction.atomic():
            order = Order.objects.create(
                order_number='PV-' + uuid4().hex[:8].upper(),
                user=request.user if request.user.is_authenticated else None,
                customer_type='particulier',
                customer_name=form.cleaned_data['name'].strip(),
                email=form.cleaned_data['email'].strip(),
                phone=form.cleaned_data['phone'].strip(),
                table_number=table_number,
                address='',
                order_type=order_type,
                collection_date=collection_date,
                collection_time=collection_time,
                accepted_terms=form.cleaned_data['accepted_terms'],
                selected_reward=selected_reward,
                promo_code=promo.code if promo else '',
                notes=(form.cleaned_data['notes'].strip() + (f'\nOffre fidélité: {loyalty_note}' if loyalty_note else '')).strip(),
                total=final_total,
                payment_status='pending' if payment_method == 'stripe' else 'cash',
            )
            for item in items:
                OrderItem.objects.create(order=order, product=item['product'], name=item['product'].name,
                    quantity=item['qty'], unit_price=item['product'].price, line_total=item['line_total'])
            if request.user.is_authenticated and loyalty_reward:
                for milestone in loyalty['available_milestones']:
                    LoyaltyRedemption.objects.create(
                        user=request.user,
                        order=order,
                        reward=loyalty_reward,
                        milestone=milestone,
                    )
        _send_order_received_email(order)
        request.session['cart'] = {}
        request.session.pop('checkout_token', None)
        pending_ids = request.session.get('pending_order_ids', [])
        request.session['pending_order_ids'] = (pending_ids + [order.id])[-5:]
        if table_number:
            request.session.pop('table_number', None)
        if payment_method == 'stripe' and settings.STRIPE_SECRET_KEY:
            return redirect('shop:stripe_checkout', order_id=order.id)
        messages.success(request, 'Commande créée. Une facture est disponible.')
        return redirect(order.get_absolute_url())
    if request.method == 'GET':
        request.session['checkout_token'] = uuid4().hex
    return render(request, 'shop/checkout.html', {
        'form': form,
        'checkout_token': request.session.get('checkout_token', ''),
        'items': items, 'subtotal': total, 'discount': discount, 'total': final_total,
        'stripe_enabled': bool(settings.STRIPE_SECRET_KEY), 'loyalty_rewards': LoyaltyReward.objects.filter(is_active=True),
        'pizza_qty': pizza_qty, 'loyalty': loyalty, 'loyalty_remaining': loyalty['remaining'],
        'loyalty_gift_eligible': bool(reward_count), 'loyalty_account_required': not request.user.is_authenticated,
        'checkout_name': checkout_name, 'checkout_email': checkout_email, 'table_number': table_number,
        'slots_available': form.has_available_slots,
        'meta_title': 'Commander une pizza à emporter à Bordeaux | Pizza Vitti',
        'meta_description': 'Finalisez votre commande Pizza Vitti et choisissez votre créneau de retrait au restaurant.',
        'meta_robots': 'noindex,nofollow',
    })

def create_checkout_session(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.id not in request.session.get('pending_order_ids', []):
        return HttpResponse('Accès refusé.', status=403)
    if not settings.STRIPE_SECRET_KEY:
        return HttpResponse('Paiement par carte indisponible.', status=503)
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode='payment',
        customer_email=order.email,
        payment_method_types=['card'],
        line_items=[{'price_data': {'currency': 'eur', 'product_data': {'name': f'Commande {order.order_number}'}, 'unit_amount': int(order.total * 100)}, 'quantity': 1}],
        success_url=(
            settings.SITE_URL
            + reverse('shop:payment_success', args=[order.order_number])
            + '?session_id={CHECKOUT_SESSION_ID}'
        ),
        cancel_url=settings.SITE_URL + reverse('shop:invoice', args=[order.order_number]),
    )
    order.stripe_session_id = session.id
    order.save(update_fields=['stripe_session_id'])
    return redirect(session.url)

def payment_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    session_id = request.GET.get('session_id', '')
    if session_id and session_id == order.stripe_session_id and settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            order.payment_status = 'paid'
            order.save(update_fields=['payment_status'])
            messages.success(request, 'Paiement par carte confirmé. Merci pour votre commande.')
        else:
            messages.warning(request, 'Le paiement est encore en cours de confirmation.')
    elif order.payment_status != 'paid':
        messages.warning(request, 'Le paiement n’a pas pu être confirmé.')
    return redirect(order.get_absolute_url())


@csrf_exempt
@require_POST
def stripe_webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=503)
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.headers.get('Stripe-Signature', ''),
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        if session.get('payment_status') == 'paid':
            Order.objects.filter(
                stripe_session_id=session.get('id'),
            ).exclude(payment_status='paid').update(payment_status='paid')
    return HttpResponse(status=200)

def invoice(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items'), order_number=order_number)
    status_order = ['received', 'preparing', 'ready', 'delivered']
    order.progress_step = status_order.index(order.status) + 1 if order.status in status_order else 0
    return render(request, 'shop/invoice.html', {'order': order})


def _safe_next_url(request, fallback):
    next_url = request.POST.get('next') or request.GET.get('next') or fallback
    return next_url if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ) else fallback


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
    if request.session.get('kitchen_access') and not _session_or_staff(request, 'owner_access'):
        selected_role = 'kitchen'
    elif request.session.get('staff_id') and not _session_or_staff(request, 'owner_access'):
        selected_role = 'staff'
    fallback = _login_fallback(selected_role)
    if selected_role == 'owner' and _session_or_staff(request, 'owner_access'):
        return redirect(_safe_next_url(request, fallback))
    if selected_role == 'kitchen' and (_session_or_staff(request, 'kitchen_access') or _session_or_staff(request, 'owner_access')):
        return redirect(_safe_next_url(request, fallback))
    if selected_role == 'staff' and request.session.get('staff_id'):
        return redirect(_safe_next_url(request, fallback))
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        django_owner = None
        if selected_role == 'owner':
            candidate = authenticate(request, username=username, password=password)
            if candidate and candidate.is_active and (candidate.is_staff or candidate.is_superuser):
                django_owner = candidate
        if selected_role == 'owner' and (
            (_owner_username_matches(username) and _owner_password_matches(password))
            or django_owner
        ):
            request.session.pop('staff_id', None)
            request.session['owner_access'] = True
            request.session['kitchen_access'] = True
            messages.success(request, 'Accès propriétaire activé.')
            return redirect(_safe_next_url(request, reverse('shop:owner_dashboard')))
        if selected_role == 'kitchen' and _password_matches(password, settings.KITCHEN_PASSWORD):
            request.session.pop('owner_access', None)
            request.session.pop('staff_id', None)
            request.session['kitchen_access'] = True
            messages.success(request, 'Accès cuisine activé.')
            return redirect(_safe_next_url(request, reverse('shop:kitchen_app')))
        if selected_role == 'staff':
            staff = StaffMember.objects.filter(username__iexact=username, is_active=True).first()
            if staff and staff.check_password(password):
                request.session.pop('owner_access', None)
                request.session.pop('kitchen_access', None)
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
    request.session.pop('kitchen_access', None)
    messages.success(request, 'Session propriétaire fermée.')
    return redirect('shop:app_login')


def camera_removed(request, unused=''):
    return HttpResponseNotFound()


def _report_stats(start, end=None):
    qs = Order.objects.filter(created_at__gte=start)
    if end:
        qs = qs.filter(created_at__lt=end)
    data = qs.aggregate(count=Count('id'), revenue=Sum('total'))
    return {'count': data['count'] or 0, 'revenue': data['revenue'] or Decimal('0.00')}


def _format_duration(seconds):
    total_minutes = max(0, int(seconds)) // 60
    hours, minutes = divmod(total_minutes, 60)
    return f'{hours} h {minutes:02d}'


def _staff_shift_total(shifts, at=None):
    return sum(shift.worked_seconds(at=at) for shift in shifts)


def _safe_date(value, fallback):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return fallback


@owner_required
def owner_dashboard(request):
    if request.method == 'POST' and request.POST.get('action') == 'update_product_availability':
        product = get_object_or_404(Product, id=request.POST.get('product_id'))
        availability_status = request.POST.get('availability_status', '')
        if availability_status not in dict(Product.AVAILABILITY):
            messages.error(request, 'Disponibilité invalide.')
            return redirect('shop:owner_dashboard')
        product.availability_status = availability_status
        product.available_again_at = None
        if availability_status == 'scheduled':
            try:
                product.available_again_at = timezone.make_aware(
                    datetime.fromisoformat(request.POST.get('available_again_at', ''))
                )
            except (TypeError, ValueError):
                messages.error(request, 'Choisissez une date et une heure valides.')
                return redirect('shop:owner_dashboard')
        product.save(update_fields=['availability_status', 'available_again_at', 'is_available', 'updated_at'])
        messages.success(request, f'Disponibilité de {product.name} mise à jour.')
        return redirect('shop:owner_dashboard')
    if request.method == 'POST' and request.POST.get('action') == 'update_loyalty_reward':
        if not settings.LOYALTY_ENABLED:
            messages.error(request, 'Le programme fidélité est temporairement désactivé.')
            return redirect('shop:owner_dashboard')
        reward_type = request.POST.get('reward_type', '')
        valid_reward_types = dict(LoyaltyReward.REWARD_TYPES)
        try:
            pizzas_required = int(request.POST.get('pizzas_required', 5))
        except (TypeError, ValueError):
            pizzas_required = 0
        if reward_type not in valid_reward_types or not 1 <= pizzas_required <= 50:
            messages.error(request, 'Choisissez un cadeau valide et un palier entre 1 et 50 pizzas.')
        else:
            LoyaltyReward.objects.update(is_active=False)
            reward, _ = LoyaltyReward.objects.get_or_create(
                reward_type=reward_type,
                pizzas_required=pizzas_required,
                defaults={'name': 'Cadeau fidélité'},
            )
            reward.name = f'Cadeau fidélité - {valid_reward_types[reward_type]}'
            reward.is_active = True
            reward.save(update_fields=['name', 'is_active', 'updated_at'])
            messages.success(request, 'Le cadeau fidélité a été mis à jour.')
        return redirect('shop:owner_dashboard')
    today_start, now = _today_bounds()
    yesterday_start = today_start - timedelta(days=1)
    active_orders = Order.objects.filter(status__in=['received','preparing','ready'])
    today_orders = Order.objects.filter(created_at__gte=today_start)
    yesterday_orders = Order.objects.filter(created_at__gte=yesterday_start, created_at__lt=today_start)
    today_staff = StaffShift.objects.select_related('staff').filter(check_in_at__date=timezone.localdate())
    present_shifts = today_staff.exclude(status='checked_out')
    stats = today_orders.aggregate(count=Count('id'), revenue=Sum('total'))
    yesterday_stats = yesterday_orders.aggregate(count=Count('id'), revenue=Sum('total'))
    orders_count = stats['count'] or 0
    revenue = stats['revenue'] or Decimal('0.00')
    yesterday_orders_count = yesterday_stats['count'] or 0
    yesterday_revenue = yesterday_stats['revenue'] or Decimal('0.00')
    average_order = revenue / orders_count if orders_count else Decimal('0.00')
    waiting_orders = active_orders.filter(status='received', created_at__lt=now - timedelta(minutes=15)).count()
    failed_payments = today_orders.filter(payment_status='failed').count()
    pending_reservations = Reservation.objects.filter(status='new', date__gte=timezone.localdate()).count()
    sold_out_count = Product.objects.exclude(availability_status='available').count()
    most_ordered = (
        OrderItem.objects.filter(order__created_at__gte=today_start)
        .values('name')
        .annotate(quantity=Sum('quantity'))
        .order_by('-quantity')[:5]
    )
    return render(request, 'shop/owner_dashboard.html', {
        'orders_count': orders_count,
        'revenue': revenue,
        'average_order': average_order,
        'cancelled_orders_count': today_orders.filter(status='cancelled').count(),
        'orders_difference': orders_count - yesterday_orders_count,
        'revenue_difference': revenue - yesterday_revenue,
        'active_orders_count': active_orders.count(),
        'staff_present_count': present_shifts.count(),
        'open_purchase_count': PurchaseOrder.objects.exclude(status__in=['received','cancelled']).count(),
        'recent_orders': Order.objects.prefetch_related('items').order_by('-created_at')[:8],
        'most_ordered': most_ordered,
        'present_shifts': present_shifts[:6],
        'received_count': active_orders.filter(status='received').count(),
        'preparing_count': active_orders.filter(status='preparing').count(),
        'ready_count': active_orders.filter(status='ready').count(),
        'waiting_orders_count': waiting_orders,
        'failed_payments_count': failed_payments,
        'pending_reservations_count': pending_reservations,
        'sold_out_count': sold_out_count,
        'dashboard_now': timezone.localtime(),
        'loyalty_reward': _active_loyalty_reward(),
        'loyalty_reward_types': LoyaltyReward.REWARD_TYPES,
        'availability_products': Product.objects.select_related('category').order_by('category__order', 'name'),
        'kitchen_app': True,
        'meta_title': 'Dashboard propriétaire | Pizza Vitti',
    })


@owner_required
def camera_center(request):
    selected_location = request.GET.get('location', '').strip()
    cameras_qs = SecurityCamera.objects.filter(is_active=True).order_by('sort_order', 'name')
    locations = list(
        CameraLocation.objects.filter(is_active=True)
        .prefetch_related(Prefetch('cameras', queryset=cameras_qs))
        .order_by('name')
    )
    if selected_location.isdigit():
        locations = [location for location in locations if location.id == int(selected_location)]
    camera_total = sum(len(location.cameras.all()) for location in locations)
    return render(request, 'shop/camera_center.html', {
        'locations': locations,
        'all_locations': CameraLocation.objects.filter(is_active=True).order_by('name'),
        'selected_location': selected_location,
        'camera_total': camera_total,
        'kitchen_app': True,
        'meta_title': 'Centre caméras | Pizza Vitti',
    })


@owner_required
def camera_detail(request, camera_id):
    camera = get_object_or_404(
        SecurityCamera.objects.select_related('location'),
        id=camera_id,
        is_active=True,
        location__is_active=True,
    )
    return render(request, 'shop/camera_detail.html', {
        'camera': camera,
        'kitchen_app': True,
        'meta_title': f'{camera.name} | Centre caméras',
    })


@owner_required
def camera_setup(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')

        def posted_id(field_name, error_message):
            value = request.POST.get(field_name, '').strip()
            if not value.isdigit():
                raise ValidationError(error_message)
            return value

        try:
            if action == 'add_location':
                location = CameraLocation(
                    name=request.POST.get('name', '').strip(),
                    kind=request.POST.get('kind', 'restaurant'),
                    address=request.POST.get('address', '').strip(),
                    gateway_url=request.POST.get('gateway_url', '').strip(),
                    notes=request.POST.get('notes', '').strip(),
                )
                location.full_clean()
                location.save()
                messages.success(request, f'Lieu « {location.name} » ajouté.')
            elif action == 'update_location':
                location = get_object_or_404(CameraLocation, id=posted_id('location_id', 'Lieu invalide.'))
                location.name = request.POST.get('name', '').strip()
                location.kind = request.POST.get('kind', 'restaurant')
                location.address = request.POST.get('address', '').strip()
                location.gateway_url = request.POST.get('gateway_url', '').strip()
                location.notes = request.POST.get('notes', '').strip()
                location.full_clean()
                location.save()
                messages.success(request, f'Lieu « {location.name} » mis à jour.')
            elif action == 'add_camera':
                location = get_object_or_404(
                    CameraLocation,
                    id=posted_id('location_id', 'Choisissez un lieu valide.'),
                )
                camera = SecurityCamera(
                    location=location,
                    name=request.POST.get('name', '').strip(),
                    stream_name=request.POST.get('stream_name', '').strip(),
                    brand=request.POST.get('brand', '').strip(),
                    model_name=request.POST.get('model_name', '').strip(),
                    custom_view_url=request.POST.get('custom_view_url', '').strip(),
                    supports_audio=request.POST.get('supports_audio') == 'on',
                    supports_talk=request.POST.get('supports_talk') == 'on',
                    sort_order=request.POST.get('sort_order') or 0,
                    notes=request.POST.get('notes', '').strip(),
                )
                camera.full_clean()
                camera.save()
                messages.success(request, f'Caméra « {camera.name} » ajoutée.')
            elif action == 'update_camera':
                camera = get_object_or_404(SecurityCamera, id=posted_id('camera_id', 'Caméra invalide.'))
                camera.name = request.POST.get('name', '').strip()
                camera.stream_name = request.POST.get('stream_name', '').strip()
                camera.brand = request.POST.get('brand', '').strip()
                camera.model_name = request.POST.get('model_name', '').strip()
                camera.custom_view_url = request.POST.get('custom_view_url', '').strip()
                camera.supports_audio = request.POST.get('supports_audio') == 'on'
                camera.supports_talk = request.POST.get('supports_talk') == 'on'
                camera.sort_order = request.POST.get('sort_order') or 0
                camera.notes = request.POST.get('notes', '').strip()
                camera.full_clean()
                camera.save()
                messages.success(request, f'Caméra « {camera.name} » mise à jour.')
            elif action == 'toggle_camera':
                camera = get_object_or_404(SecurityCamera, id=posted_id('camera_id', 'Caméra invalide.'))
                camera.is_active = not camera.is_active
                camera.save(update_fields=['is_active','updated_at'])
                messages.success(request, 'Statut de la caméra mis à jour.')
            elif action == 'delete_camera':
                camera = get_object_or_404(SecurityCamera, id=posted_id('camera_id', 'Caméra invalide.'))
                camera_name = camera.name
                camera.delete()
                messages.success(request, f'Caméra « {camera_name} » supprimée.')
            elif action == 'toggle_location':
                location = get_object_or_404(CameraLocation, id=posted_id('location_id', 'Lieu invalide.'))
                location.is_active = not location.is_active
                location.save(update_fields=['is_active','updated_at'])
                messages.success(request, 'Statut du lieu mis à jour.')
            else:
                messages.error(request, 'Action caméra inconnue.')
        except ValidationError as error:
            details = ' '.join(
                message
                for field_messages in error.message_dict.values()
                for message in field_messages
            ) if hasattr(error, 'message_dict') else ' '.join(error.messages)
            messages.error(request, details)
        return redirect('shop:camera_setup')
    return render(request, 'shop/camera_setup.html', {
        'locations': CameraLocation.objects.prefetch_related('cameras').order_by('name'),
        'location_kinds': CameraLocation.KINDS,
        'kitchen_app': True,
        'meta_title': 'Configuration caméras | Pizza Vitti',
    })


@owner_required
def camera_gateway_guide(request):
    return render(request, 'shop/camera_gateway_guide.html', {
        'kitchen_app': True,
        'meta_title': 'Guide gateway caméras | Pizza Vitti',
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
        role = request.POST.get('role', '').strip()
        valid_roles = dict(StaffMember.ROLE_CHOICES)
        if role not in valid_roles:
            role = 'server'
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
        recent_shifts = list(staff.shifts.filter(check_in_at__gte=timezone.now() - timedelta(days=30)))
        staff.month_hours = _format_duration(_staff_shift_total(recent_shifts))
    return render(request, 'shop/staff_manage.html', {
        'staff_members': staff_members,
        'role_choices': StaffMember.ROLE_CHOICES,
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
    today = timezone.localdate()
    default_start = today - timedelta(days=today.weekday())
    start_date = _safe_date(request.GET.get('date_from'), default_start)
    end_date = _safe_date(request.GET.get('date_to'), today)
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    selected_staff_id = request.GET.get('staff_id', '').strip()
    staff_shifts_qs = (
        StaffShift.objects.select_related('staff')
        .filter(check_in_at__date__gte=start_date, check_in_at__date__lte=end_date)
        .order_by('-check_in_at')
    )
    if selected_staff_id.isdigit():
        staff_shifts_qs = staff_shifts_qs.filter(staff_id=int(selected_staff_id))
    staff_shifts = list(staff_shifts_qs)
    staff_totals = {}
    for shift in staff_shifts:
        summary = staff_totals.setdefault(shift.staff_id, {
            'staff': shift.staff,
            'seconds': 0,
            'shifts': 0,
        })
        summary['seconds'] += shift.worked_seconds(at=now)
        summary['shifts'] += 1
        shift.hours_display = _format_duration(shift.worked_seconds(at=now))
        shift.pause_display = _format_duration(
            shift.break_seconds + (
                max(0, int((now - shift.break_started_at).total_seconds()))
                if shift.status == 'break' and shift.break_started_at else 0
            )
        )
    staff_summaries = sorted(staff_totals.values(), key=lambda item: item['staff'].name.lower())
    for summary in staff_summaries:
        summary['hours_display'] = _format_duration(summary['seconds'])
    total_staff_seconds = sum(summary['seconds'] for summary in staff_summaries)
    return render(request, 'shop/reports_dashboard.html', {
        'reports': reports,
        'staff_shifts': staff_shifts,
        'staff_summaries': staff_summaries,
        'staff_members': StaffMember.objects.filter(is_active=True),
        'selected_staff_id': selected_staff_id,
        'date_from': start_date.isoformat(),
        'date_to': end_date.isoformat(),
        'total_staff_hours': _format_duration(total_staff_seconds),
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
    today_shifts = list(StaffShift.objects.filter(staff=staff, check_in_at__date=today).order_by('-created_at'))
    shift = today_shifts[0] if today_shifts else None
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    history = list(StaffShift.objects.filter(staff=staff).order_by('-check_in_at')[:30])
    week_shifts = list(StaffShift.objects.filter(staff=staff, check_in_at__date__gte=week_start))
    month_shifts = list(StaffShift.objects.filter(staff=staff, check_in_at__date__gte=month_start))
    for item in history:
        item.hours_display = _format_duration(item.worked_seconds())
    return render(request, 'shop/staff_portal.html', {
        'staff_member': staff,
        'shift': shift,
        'history': history,
        'today_hours': _format_duration(_staff_shift_total(today_shifts)),
        'week_hours': _format_duration(_staff_shift_total(week_shifts)),
        'month_hours': _format_duration(_staff_shift_total(month_shifts)),
        'active_work_seconds': shift.worked_seconds() if shift else 0,
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
            messages.success(request, 'Entrée enregistrée.')
        else:
            messages.info(request, 'Vous êtes déjà pointé.')
    elif shift and action == 'break' and shift.status == 'checked_in':
        shift.status = 'break'
        shift.break_started_at = now
        shift.save(update_fields=['status','break_started_at','updated_at'])
        messages.success(request, 'Pause démarrée.')
    elif shift and action == 'back' and shift.status == 'break':
        if shift.break_started_at:
            shift.break_seconds += max(0, int((now - shift.break_started_at).total_seconds()))
        shift.status = 'checked_in'
        shift.break_ended_at = now
        shift.save(update_fields=['status','break_ended_at','break_seconds','updated_at'])
        messages.success(request, 'Retour de pause enregistré.')
    elif shift and action == 'check_out' and shift.status != 'checked_out':
        if shift.status == 'break' and shift.break_started_at:
            shift.break_seconds += max(0, int((now - shift.break_started_at).total_seconds()))
            shift.break_ended_at = now
        shift.status = 'checked_out'
        shift.check_out_at = now
        shift.save(update_fields=['status','check_out_at','break_ended_at','break_seconds','updated_at'])
        messages.success(request, 'Sortie enregistrée.')
    else:
        messages.info(request, 'Cette action n’est pas disponible avec votre statut actuel.')
    return redirect('shop:staff_portal')


@kitchen_required
def qr_tables(request):
    try:
        count = min(max(int(request.GET.get('count', 20)), 1), 80)
    except ValueError:
        count = 20
    base_url = request.build_absolute_uri(localized_url('home', 'fr')).rstrip('/')
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
        email = request.POST.get('email','').strip()
        order = Order.objects.filter(order_number__iexact=number, email__iexact=email).first()
        if not order: messages.error(request, 'Commande introuvable. Vérifiez le numéro et l’adresse email.')
    if order:
        status_order = ['received', 'preparing', 'ready', 'delivered']
        order.progress_step = status_order.index(order.status) + 1 if order.status in status_order else 0
    return render(request, 'shop/track_order.html', {'order': order, 'meta_robots': 'noindex,nofollow'})

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


def _assistant_menu_context():
    lines = []
    products = (
        Product.objects.filter(professional_only=False)
        .select_related('category')
        .order_by('category__order', 'category__name', 'name')[:90]
    )
    for product in products:
        category = product.category.name if product.category else 'Menu'
        details = [product.description.strip()]
        if product.allergens:
            details.append(f'Allergènes déclarés : {product.allergens}')
        if product.is_vegetarian:
            details.append('végétarien')
        availability = product.get_availability_status_display()
        lines.append(
            f'- {category} | {product.name} | {product.price:.2f} € / {product.unit} | '
            f'{availability} | {"; ".join(part for part in details if part)}'
        )
    return '\n'.join(lines)


def _openai_assistant_reply(message, table_number=''):
    if not settings.OPENAI_API_KEY:
        return ''
    table_context = f'Le client est à la table {table_number}.' if table_number else 'Aucune table QR n’est associée à cette conversation.'
    instructions = f"""
Tu es l’assistant officiel de Pizza Vitti - Ornano, 236 rue d’Ornano, 33000 Bordeaux.
Réponds dans la langue utilisée par le client, avec un ton chaleureux, clair et concis.
Tu aides uniquement pour le restaurant : menu, prix, ingrédients, allergènes, commande, réservation,
retrait, paiement, fidélité, adresse et avis. Ne prétends jamais avoir confirmé une réservation,
modifié ou remboursé une commande. Ne donne jamais de conseil médical sur les allergènes : demande
au client de confirmer auprès du restaurant. Si une information n’est pas fournie ci-dessous,
dis-le honnêtement et propose la page Contact. N’invente aucun plat, prix, horaire ou disponibilité.
{table_context}

MENU ACTUEL DU SITE :
{_assistant_menu_context()}
""".strip()
    try:
        response = requests.post(
            'https://api.openai.com/v1/responses',
            headers={
                'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': settings.OPENAI_MODEL,
                'instructions': instructions,
                'input': message[:1200],
                'max_output_tokens': 350,
            },
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        output = response.json().get('output') or []
        parts = []
        for item in output:
            if item.get('type') != 'message':
                continue
            for content in item.get('content') or []:
                if content.get('type') == 'output_text' and content.get('text'):
                    parts.append(content['text'].strip())
        return '\n'.join(parts).strip()
    except (requests.RequestException, ValueError, TypeError):
        return ''

def contact(request):
    if request.method == 'POST':
        CustomerMessage.objects.create(name=request.POST.get('name',''), email=request.POST.get('email',''), phone=request.POST.get('phone',''), subject=request.POST.get('subject',''), message=request.POST.get('message',''))
        messages.success(request, 'Votre message a bien été envoyé à Pizza Vitti.')
        return redirect('shop:contact')
    return render(request, 'shop/contact.html')

@require_POST
def bot_reply(request):
    raw_message = request.POST.get('message', '').strip()[:1200]
    msg = raw_message.lower()
    lang = request.POST.get('lang', 'fr')
    if lang not in TRANSLATIONS:
        lang = 'fr'
    assistant_copy = t_for(lang)
    english = any(word in msg for word in [' are ', ' you ', 'what', 'where', 'when', 'how', 'open', 'hello', 'please'])
    table_number = request.session.get('table_number', '').strip()
    ai_answer = _openai_assistant_reply(raw_message, table_number) if raw_message else ''
    if ai_answer:
        answer = ai_answer
    elif any(w in msg for w in ['table', 'qr', 'scan', 'scanner']):
        answer = f"Vous êtes sur la table {table_number}. Ajoutez vos plats au panier puis validez la commande." if table_number else "Scannez le QR code posé sur votre table : le site mémorise la table, puis vous pouvez commander depuis le menu."
    elif any(w in msg for w in ['menu', 'pizza', 'pasta', 'pâtes', 'raviol', 'boisson', 'dessert', 'pizze', 'pizzas', '披萨', 'ピザ', 'بيتزا']):
        answer = assistant_copy['assistant_menu_answer']
    elif settings.LOYALTY_ENABLED and any(w in msg for w in ['fidélité', 'fidelite', 'cadeau', '5 pizza', '5 pizzas']):
        reward = _active_loyalty_reward()
        pizzas_required = reward.pizzas_required if reward else 5
        gift = reward.get_reward_type_display() if reward else 'un cadeau Pizza Vitti'
        answer = f"Offre fidélité : {pizzas_required} pizzas commandées avec votre compte = {gift}. Créez votre carte fidélité ou connectez-vous avant de valider la commande."
    elif any(w in msg for w in ['payer', 'visa', 'carte', 'paiement', 'stripe', 'cash', 'espèce', 'espece']):
        answer = "Vous pouvez payer par carte bancaire si Stripe est configuré, ou choisir le paiement au retrait / sur place selon l’organisation du restaurant."
    elif any(w in msg for w in ['réserver', 'reserver', 'reservation', 'réservation', 'book', 'reservar', 'prenot', 'reserveer', '预订', '予約', 'احجز', 'حجز']):
        answer = assistant_copy['assistant_booking_answer']
    elif any(w in msg for w in ['horaire', 'heures', 'ouvert', 'ouverte', 'open', 'opening hours', 'close', 'closing']):
        answer = (
            "For today's opening status, please check the Pizza Vitti – Ornano Google listing or call the restaurant, as exceptional hours can change."
            if english else
            "Pour savoir si le restaurant est ouvert aujourd’hui, consultez la fiche Google Pizza Vitti – Ornano ou appelez le restaurant, car les horaires exceptionnels peuvent changer."
        )
    elif any(w in msg for w in ['adresse', 'où', 'localisation', 'maps', 'venir']):
        answer = "Pizza Vitti se trouve au 236 Rue d'Ornano, 33000 Bordeaux. Vous pouvez ouvrir Google Maps depuis la page contact ou le pied de page."
    elif any(w in msg for w in ['allerg', 'végétarien', 'vegetarien', 'sans gluten', 'halal', 'alérgen', 'alerg', '过敏', 'アレルゲン', 'الحساسية']):
        answer = assistant_copy['assistant_allergen_answer']
    elif any(w in msg for w in ['suivi', 'statut', 'prête', 'prete', 'préparation', 'preparation']):
        answer = "Après commande, conservez votre numéro de commande. La facture affiche le statut : reçue, en préparation, prête ou servie."
    elif any(w in msg for w in ['avis', 'review', 'google', 'commentaire']):
        answer = "Après votre commande, vous pouvez laisser un avis depuis la page Avis. Vos commentaires Google aident beaucoup Pizza Vitti."
    elif any(w in msg for w in ['bonjour', 'salut', 'hello', 'hi']):
        answer = (
            "Hello! I can help you choose from the menu, order at your table, book, or track an order."
            if english else
            "Bonjour ! Je peux vous aider à choisir le menu, commander à table, réserver ou suivre une commande."
        )
    else:
        answer = (
            "I can help with the menu, pizzas, pasta, drinks, table ordering, bookings, payments, allergens and Google reviews. Please ask a restaurant-related question."
            if english else
            "Je peux vous aider pour le menu, les pizzas, les pastas, les boissons, la commande QR à table, la réservation, le paiement, les allergènes et les avis Google."
        )
    return JsonResponse({'answer': answer})



def booking(request):
    form = ReservationForm(request.POST or None)
    booking_copy = t_for(get_lang_from_path(request.path))
    booking_labels = {
        'name': booking_copy['name'], 'email': booking_copy['email'],
        'phone': booking_copy['phone'], 'guests': booking_copy['guests'],
        'date': booking_copy['date'], 'time': booking_copy['time'],
        'message': booking_copy['message'],
    }
    for field_name, label in booking_labels.items():
        form.fields[field_name].label = label
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request,
            'Votre demande a bien été envoyée. La réservation sera confirmée par Pizza Vitti par e-mail ou téléphone.',
        )
        return redirect('shop:booking')
    return render(request, 'shop/booking.html', {
        'form': form,
        'meta_title': 'Réserver une table chez Pizza Vitti Bordeaux',
        'meta_description': 'Envoyez votre demande de réservation à Pizza Vitti, 236 rue d’Ornano à Bordeaux.',
    })

def reviews(request):
    reviews = Review.objects.filter(is_published=True).exclude(source_url='')
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
    return redirect(_safe_next_url(request, localized_url('home', 'fr')))

def simple_page(request, title):
    return render(request, 'shop/simple.html', {'title': title})


def legal_notice(request):
    return render(request, 'shop/legal_notice.html', {
        'meta_title': 'Mentions légales | Pizza Vitti',
        'meta_description': 'Mentions légales du site Pizza Vitti Bordeaux.',
    })


def legacy_legal_redirect(request):
    return HttpResponsePermanentRedirect(reverse('shop:mentions'))


def terms(request):
    return render(request, 'shop/terms.html', {
        'meta_title': 'Conditions générales de commande | Pizza Vitti',
        'meta_description': 'Conditions applicables aux commandes à emporter passées sur le site Pizza Vitti.',
    })


def privacy_policy(request):
    return render(request, 'shop/privacy_policy.html', {
        'meta_title': 'Politique de confidentialité | Pizza Vitti',
        'meta_description': 'Informations sur les données utilisées par le site et l’application Pizza Vitti.',
    })


def account_deletion(request):
    if request.method == 'POST' and request.POST.get('action') == 'delete_now':
        if not request.user.is_authenticated:
            messages.error(request, 'Connectez-vous pour supprimer directement votre compte.')
            return redirect(f"{reverse('account_login')}?next={reverse('shop:account_deletion')}")
        if request.POST.get('confirm') != 'yes':
            messages.error(request, 'Cochez la confirmation avant de supprimer le compte.')
            return redirect('shop:account_deletion')

        user = request.user
        email = user.email.strip()
        with transaction.atomic():
            Order.objects.filter(user=user).update(
                user=None,
                customer_name='Compte supprimé',
                email='',
                phone='',
                address='',
                notes='',
                delivery_issue_note='',
                stripe_session_id='',
            )
            if email:
                NewsletterSubscriber.objects.filter(email__iexact=email).delete()
                Reservation.objects.filter(email__iexact=email).delete()
                CustomerMessage.objects.filter(email__iexact=email).delete()
            user.delete()
        logout(request)
        messages.success(request, 'Votre compte Pizza Vitti et les données associées ont été supprimés.')
        return redirect(localized_url('home', 'fr'))

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if not email:
            messages.error(request, 'Indiquez l’adresse e-mail du compte à supprimer.')
        else:
            CustomerMessage.objects.create(
                name='Demande de suppression de compte',
                email=email,
                subject='Suppression de compte Pizza Vitti',
                message='Demande de suppression envoyée depuis la page publique Google Play.',
            )
            messages.success(
                request,
                'Votre demande est enregistrée. Pizza Vitti la traitera dans les meilleurs délais.',
            )
            return redirect('shop:account_deletion')

    return render(request, 'shop/account_deletion.html', {
        'meta_title': 'Supprimer mon compte | Pizza Vitti',
        'meta_description': 'Supprimer un compte client Pizza Vitti et ses données associées.',
    })


def localized_dispatch(request, lang, page=None):
    if lang not in TRANSLATIONS:
        return redirect(localized_url('home', 'fr'))
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
    loyalty = _loyalty_status(request.user)
    favorites = Favorite.objects.filter(user=request.user).select_related('product', 'product__category')[:12]
    return render(request, 'shop/customer_dashboard.html', {
        'orders': orders,
        'loyalty': loyalty,
        'loyalty_steps': range(1, loyalty['pizzas_required'] + 1),
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
    return redirect(_safe_next_url(request, product.get_absolute_url()))

def robots_txt(request):
    sitemap_url = settings.SITE_URL.rstrip('/') + '/sitemap.xml'
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /accounts/\n"
        "Disallow: /owner/\n"
        "Disallow: /kitchen/\n"
        "Disallow: /staff/\n"
        "Disallow: /panier/\n"
        "Disallow: /commande/\n"
        f"Sitemap: {sitemap_url}\n"
    )
    return HttpResponse(content, content_type='text/plain')


def android_asset_links(request):
    fingerprints = settings.ANDROID_CERT_SHA256_FINGERPRINTS
    links = []
    if fingerprints:
        links.append({
            'relation': ['delegate_permission/common.handle_all_urls'],
            'target': {
                'namespace': 'android_app',
                'package_name': settings.ANDROID_APP_PACKAGE,
                'sha256_cert_fingerprints': fingerprints,
            },
        })
    return HttpResponse(
        json.dumps(links),
        content_type='application/json',
        headers={'Cache-Control': 'public, max-age=300'},
    )


def manifest_webmanifest(request):
    site_url = request.build_absolute_uri('/').rstrip('/')
    manifest = {
        'name': 'Pizza Vitti',
        'short_name': 'Vitti App',
        'description': 'Menu, commandes et informations de Pizza Vitti.',
        'id': '/fr/',
        'start_url': '/fr/',
        'scope': '/',
        'display': 'standalone',
        'display_override': ['window-controls-overlay', 'standalone'],
        'orientation': 'any',
        'background_color': '#171923',
        'theme_color': '#171923',
        'categories': ['food', 'shopping'],
        'shortcuts': [
            {'name': 'Carte Pizza Vitti', 'short_name': 'Menu', 'url': '/fr/'},
            {'name': 'Commander', 'short_name': 'Commander', 'url': '/fr/menu/pizzas/'},
            {'name': 'Réserver', 'short_name': 'Réserver', 'url': '/fr/reserver/'},
        ],
        'icons': [
            {'src': f'{site_url}/static/shop/img/pwa/icon-192.png', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any maskable'},
            {'src': f'{site_url}/static/shop/img/pwa/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'},
        ],
    }
    return HttpResponse(json.dumps(manifest), content_type='application/manifest+json')

def service_worker(request):
    content = """
const CACHE_NAME = 'pizza-vitti-app-v8';
const STATIC_ASSETS = [
  '/static/shop/style.css',
  '/static/shop/app.js',
  '/static/shop/dist/site.css',
  '/static/shop/dist/site.js',
  '/static/shop/img/logo-vitti-header.png',
  '/static/shop/img/store/google-play-badge-fr.png',
  '/static/shop/img/hero/menu-pizza-vitti.jpg',
  '/static/shop/img/hero/menu-pasta.jpg',
  '/static/shop/img/hero/menu-bambino-pizza.jpg',
  '/static/shop/img/hero/menu-tiramisu.jpg',
  '/static/shop/img/hero/blog-pizza-vitti.jpg',
  '/static/shop/img/hero/loyalty-pizza-vitti.jpg',
  '/static/shop/img/chat/lets-chat-reference.png',
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
    return HttpResponse(
        content.strip(),
        content_type='application/javascript',
        headers={'Cache-Control': 'no-cache, no-store, must-revalidate'},
    )
