
from django.conf import settings
from .models import Category
from django.db.models import Case, When, IntegerField
from .translations import LANGUAGE_OPTIONS, get_lang_from_path, t_for, localized_url, lang_home

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


def site_settings(request):
    lang = get_lang_from_path(request.path)
    T = t_for(lang)
    return {
        'SITE_URL': settings.SITE_URL,
        'WHATSAPP_NUMBER': settings.WHATSAPP_NUMBER,
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
    return {'cart_count': sum(int(q) for q in cart.values())}
