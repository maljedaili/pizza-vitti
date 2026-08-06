import json

from django.conf import settings
from .hours import restaurant_status, weekly_hours
from .models import BlogPost, Category, Product, ProductTranslation, SiteConfiguration
from django.db.models import Case, When, IntegerField
from django.urls import reverse
from .translations import HOME_SLUGS, LANGUAGE_OPTIONS, PAGE_SLUGS, get_lang_from_path, t_for, localized_url, lang_home
from .seo import absolute_public_url, public_origin
from .translation_quality import is_complete_product_translation

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
    status['label'] = T['open_now'] if status['is_open'] else T['closed']
    detail_kind = status.get('detail_kind')
    detail_time = status.get('detail_time')
    if detail_kind == 'unavailable':
        status['detail'] = T['hours_unavailable']
    elif detail_kind == 'closes_at':
        status['detail'] = f"{T['closes_at']} {detail_time:%H:%M}"
    elif detail_kind == 'opens_today':
        status['detail'] = f"{T['opens_today']} {detail_time:%H:%M}"
    elif detail_kind == 'opens_tomorrow':
        status['detail'] = f"{T['opens_tomorrow']} {detail_time:%H:%M}"
    elif detail_kind == 'opens_weekday':
        day = T['weekdays'][status['detail_weekday']]
        status['detail'] = T['opens_on'].format(day=day) + f" {detail_time:%H:%M}"
    for row in hours:
        row['label'] = T['weekdays'][row['weekday']]
        if not row['periods']:
            row['display'] = T['closed']
    configured_site_url = public_origin(request)
    site = SiteConfiguration.load()
    resolver_name = request.resolver_match.url_name if request.resolver_match else ''
    language_menu = []
    available_language_codes = None
    product_is_indexable = True
    localized_page_key = None
    if resolver_name == 'localized_page':
        current_slug = request.resolver_match.kwargs.get('page')
        localized_page_key = next(
            (key for key, slugs in PAGE_SLUGS.items() if slugs.get(lang) == current_slug),
            None,
        )
    if resolver_name == 'localized_product_detail':
        product_slug = request.resolver_match.kwargs.get('slug')
        product_is_indexable = Product.objects.filter(slug=product_slug).values_list('is_indexable', flat=True).first()
        translations = ProductTranslation.objects.filter(
            product__slug=product_slug,
        ).select_related('product')
        translated_codes = {
            translation.language
            for translation in translations
            if is_complete_product_translation(translation)
        }
        available_language_codes = {'fr', *translated_codes}
    for code, label, name, default_href in LANGUAGE_OPTIONS:
        if available_language_codes is not None and code not in available_language_codes:
            continue
        href = default_href
        if resolver_name == 'localized_menu_group':
            group = request.resolver_match.kwargs.get('group')
            if group:
                href = reverse('shop:localized_menu_group', args=[code, group])
        elif resolver_name == 'localized_product_detail':
            slug = request.resolver_match.kwargs.get('slug')
            if slug:
                href = reverse('shop:localized_product_detail', args=[code, slug])
        elif localized_page_key:
            href = localized_url(localized_page_key, code)
        elif resolver_name in {'home', 'localized_home_short'}:
            href = localized_url('home', code)
        language_menu.append((code, label, name, href))
    private_page_names = {
        'cart', 'checkout', 'invoice', 'track_order', 'customer_dashboard',
        'customer_orders', 'customer_favorites', 'account_deletion', 'app_home',
        'app_login', 'owner_dashboard', 'kitchen_app', 'staff_portal',
    }
    same_as = [url for url in (
        site.google_business_profile_url, site.instagram_url, site.facebook_url,
        site.tiktok_url, site.youtube_url,
    ) if url]
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
        '@type': ['Restaurant', 'LocalBusiness'],
        '@id': configured_site_url + '/#restaurant',
        'name': site.restaurant_name,
        'alternateName': 'Pizza Vitti - Ornano',
        'description': T['default_meta_description'],
        'image': [
            configured_site_url + '/static/shop/img/hero/menu-pizza-vitti.jpg',
            configured_site_url + '/static/shop/img/hero/pizza-vitti-deliveroo.jpg',
        ],
        'logo': configured_site_url + '/static/shop/img/logo-vitti-header.png',
        'servesCuisine': [value.strip() for value in site.cuisine_types.split(',') if value.strip()],
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': site.street_address,
            'addressLocality': site.city,
            'postalCode': site.postal_code,
            'addressCountry': site.country_code,
        },
        'geo': {
            '@type': 'GeoCoordinates',
            'latitude': float(site.latitude),
            'longitude': float(site.longitude),
        },
        'telephone': site.telephone,
        'url': configured_site_url,
        'hasMap': site.google_maps_url,
        'hasMenu': configured_site_url + localized_url('menu', lang),
        'acceptsReservations': True,
        'priceRange': site.price_range,
        'currenciesAccepted': 'EUR',
        'paymentAccepted': site.accepted_payments,
        'areaServed': {'@type': 'City', 'name': 'Bordeaux'},
        'potentialAction': [
            {
                '@type': 'OrderAction',
                'target': configured_site_url + localized_url('menu', lang),
            },
            {
                '@type': 'ReserveAction',
                'target': configured_site_url + localized_url('booking', lang),
            },
        ],
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
    partner_urls = [site.uber_eats_url, site.deliveroo_url, site.just_eat_url]
    structured_data['sameAs'] = list(dict.fromkeys(structured_data.get('sameAs', []) + [url for url in partner_urls if url]))
    is_localized_home = (
        resolver_name == 'localized_page'
        and request.resolver_match.kwargs.get('page') == HOME_SLUGS.get(lang)
    )
    translation_incomplete = (
        resolver_name == 'localized_product_detail'
        and lang != 'fr'
        and available_language_codes is not None
        and lang not in available_language_codes
    )
    return {
        'site_config': site,
        'restaurant_status': status,
        'weekly_hours': hours,
        'structured_data': json.dumps(structured_data, ensure_ascii=False),
        'show_blog': True,
        'show_app_promo': resolver_name in {'home', 'localized_home_short', 'customer_dashboard'} or is_localized_home,
        'show_review_prompt': resolver_name in {'reviews', 'invoice'},
        'meta_robots': 'noindex,follow' if translation_incomplete or product_is_indexable is False else 'noindex,nofollow' if (
            resolver_name in private_page_names
            or any(segment in request.path for segment in ('/panier/', '/commande/', '/checkout/', '/cart/'))
        ) else '',
        'translation_incomplete': translation_incomplete,
        'SITE_URL': configured_site_url,
        'CANONICAL_URL': absolute_public_url(request.path, request),
        'WHATSAPP_NUMBER': settings.WHATSAPP_NUMBER,
        'GOOGLE_REVIEW_URL': site.google_review_url or settings.GOOGLE_REVIEW_URL,
        'INSTAGRAM_URL': site.instagram_url,
        'FACEBOOK_URL': site.facebook_url,
        'GOOGLE_PLAY_URL': 'https://play.google.com/store/apps/details?id=kayen.fr',
        'LOYALTY_ENABLED': settings.LOYALTY_ENABLED,
        'current_lang': lang,
        'T': T,
        'LANGUAGES_MENU': language_menu,
        'X_DEFAULT_URL': language_menu[0][3] if language_menu else localized_url('home', 'fr'),
        'GOOGLE_SITE_VERIFICATION': settings.GOOGLE_SITE_VERIFICATION,
        'BING_SITE_VERIFICATION': settings.BING_SITE_VERIFICATION,
        'GA4_MEASUREMENT_ID': settings.GA4_MEASUREMENT_ID,
        'GOOGLE_TAG_MANAGER_ID': settings.GOOGLE_TAG_MANAGER_ID,
        'MICROSOFT_CLARITY_ID': settings.MICROSOFT_CLARITY_ID,
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
    products = Product.objects.filter(id__in=cart.keys())
    items, total = [], 0
    available_count = 0
    for product in products:
        if not product.is_orderable:
            continue
        qty = max(1, int(cart.get(str(product.id), 1)))
        available_count += qty
        line_total = product.price * qty
        total += line_total
        items.append({'product': product, 'qty': qty, 'line_total': line_total})
    return {
        'cart_count': available_count,
        'cart_preview_items': items[:5],
        'cart_preview_total': total,
        'cart_preview_more': max(0, len(items) - 5),
    }
