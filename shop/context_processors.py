import json

from django.conf import settings
from .hours import restaurant_status, weekly_hours
from .models import BlogPost, Category, Product, SiteConfiguration
from django.db.models import Case, When, IntegerField
from django.urls import reverse
from .translations import LANGUAGE_OPTIONS, get_lang_from_path, t_for, localized_url, lang_home

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


def site_settings(request):
    lang = get_lang_from_path(request.path)
    T = t_for(lang)
    status = restaurant_status()
    hours = weekly_hours()
    if lang == 'ar':
        status['label'] = 'مفتوح الآن' if status['is_open'] else 'مغلق'
        status['detail'] = 'تحقق من ساعات العمل أدناه'
        arabic_days = ('الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد')
        for row, day_name in zip(hours, arabic_days):
            row['label'] = day_name
            if row['display'] == 'Fermé':
                row['display'] = 'مغلق'
    configured_site_url = settings.SITE_URL.rstrip('/')
    host = request.get_host().split(':')[0]
    if configured_site_url.startswith('http://localhost') and host not in ['localhost', '127.0.0.1']:
        configured_site_url = f"{request.scheme}://{request.get_host()}"
    site = SiteConfiguration.load()
    resolver_name = request.resolver_match.url_name if request.resolver_match else ''
    language_menu = []
    for code, label, name, default_href in LANGUAGE_OPTIONS:
        href = default_href
        if resolver_name == 'localized_menu_group':
            group = request.resolver_match.kwargs.get('group')
            if group:
                href = reverse('shop:localized_menu_group', args=[code, group])
        language_menu.append((code, label, name, href))
    private_page_names = {
        'cart', 'checkout', 'invoice', 'track_order', 'customer_dashboard',
        'customer_orders', 'customer_favorites', 'account_deletion', 'app_home',
        'app_login', 'owner_dashboard', 'kitchen_app', 'staff_portal',
    }
    same_as = [url for url in (site.instagram_url, site.facebook_url) if url]
    schema_weekdays = {
        0: 'https://schema.org/Monday',
        1: 'https://schema.org/Tuesday',
        2: 'https://schema.org/Wednesday',
        3: 'https://schema.org/Thursday',
        4: 'https://schema.org/Friday',
        5: 'https://schema.org/Saturday',
        6: 'https://schema.org/Sunday',
    }
    structured_data = {
        '@context': 'https://schema.org',
        '@type': 'Restaurant',
        'name': site.restaurant_name,
        'servesCuisine': ['Italian', 'Pizza'],
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': '236 rue d’Ornano',
            'addressLocality': 'Bordeaux',
            'postalCode': '33000',
            'addressCountry': 'FR',
        },
        'telephone': site.telephone,
        'url': configured_site_url,
        'hasMenu': configured_site_url + localized_url('menu', lang),
        'acceptsReservations': True,
        'priceRange': '€€',
        'openingHoursSpecification': [
            {
                '@type': 'OpeningHoursSpecification',
                'dayOfWeek': schema_weekdays[row['weekday']],
                'opens': f'{start:%H:%M}',
                'closes': f'{end:%H:%M}',
            }
            for row in hours
            for start, end in row['periods']
        ],
    }
    if same_as:
        structured_data['sameAs'] = same_as
    return {
        'site_config': site,
        'restaurant_status': status,
        'weekly_hours': hours,
        'structured_data': json.dumps(structured_data, ensure_ascii=False),
        'show_blog': BlogPost.objects.filter(is_published=True, body__regex=r'.{300,}').exists(),
        'show_app_promo': resolver_name in {'home', 'localized_home_short', 'customer_dashboard'},
        'show_review_prompt': resolver_name in {'reviews', 'invoice'},
        'meta_robots': 'noindex,nofollow' if (
            resolver_name in private_page_names
            or any(segment in request.path for segment in ('/panier/', '/commande/', '/checkout/', '/cart/'))
        ) else '',
        'SITE_URL': configured_site_url,
        'WHATSAPP_NUMBER': settings.WHATSAPP_NUMBER,
        'GOOGLE_REVIEW_URL': site.google_review_url or settings.GOOGLE_REVIEW_URL,
        'INSTAGRAM_URL': site.instagram_url,
        'FACEBOOK_URL': site.facebook_url,
        'GOOGLE_PLAY_URL': (
            site.google_play_url
            or settings.GOOGLE_PLAY_URL
            or 'https://play.google.com/apps/testing/kayen.fr'
        ),
        'LOYALTY_ENABLED': settings.LOYALTY_ENABLED,
        'nav_categories': _menu_category_order(Category.objects.filter(is_active=True)),
        'current_lang': lang,
        'T': T,
        'LANGUAGES_MENU': language_menu,
        'lang_home': lang_home(lang),
        'url_home': localized_url('home', lang),
        'url_menu': localized_url('menu', lang),
        'url_booking': localized_url('booking', lang),
        'url_reviews': localized_url('reviews', lang),
        'url_gallery': localized_url('gallery', lang),
        'url_blog': localized_url('blog', lang),
        'url_contact': localized_url('contact', lang),
        'url_cart': localized_url('cart', lang),
        'url_checkout': localized_url('checkout', lang),
    }

def cart_info(request):
    cart = request.session.get('cart', {})
    products = Product.objects.filter(id__in=cart.keys(), is_available=True)
    items, total = [], 0
    for product in products:
        qty = max(1, int(cart.get(str(product.id), 1)))
        line_total = product.price * qty
        total += line_total
        items.append({'product': product, 'qty': qty, 'line_total': line_total})
    return {
        'cart_count': sum(int(q) for q in cart.values()),
        'cart_preview_items': items[:5],
        'cart_preview_total': total,
        'cart_preview_more': max(0, len(items) - 5),
    }
