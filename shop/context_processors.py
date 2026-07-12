
from django.conf import settings
from .models import Category, Product
from django.db.models import Case, When, IntegerField
from .translations import LANGUAGE_OPTIONS, get_lang_from_path, t_for, localized_url, lang_home

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


def site_settings(request):
    lang = get_lang_from_path(request.path)
    T = t_for(lang)
    configured_site_url = settings.SITE_URL.rstrip('/')
    host = request.get_host().split(':')[0]
    if configured_site_url.startswith('http://localhost') and host not in ['localhost', '127.0.0.1']:
        configured_site_url = f"{request.scheme}://{request.get_host()}"
    return {
        'SITE_URL': configured_site_url,
        'WHATSAPP_NUMBER': settings.WHATSAPP_NUMBER,
        'GOOGLE_REVIEW_URL': settings.GOOGLE_REVIEW_URL,
        'INSTAGRAM_URL': settings.INSTAGRAM_URL,
        'FACEBOOK_URL': settings.FACEBOOK_URL,
        'nav_categories': _menu_category_order(Category.objects.filter(is_active=True)),
        'current_lang': lang,
        'T': T,
        'LANGUAGES_MENU': LANGUAGE_OPTIONS,
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
