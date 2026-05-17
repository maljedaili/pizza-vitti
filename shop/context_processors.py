
from django.conf import settings
from .models import Category
from .translations import LANGUAGE_OPTIONS, get_lang_from_path, t_for, localized_url, lang_home

def site_settings(request):
    lang = get_lang_from_path(request.path)
    T = t_for(lang)
    return {
        'SITE_URL': settings.SITE_URL,
        'WHATSAPP_NUMBER': settings.WHATSAPP_NUMBER,
        'nav_categories': Category.objects.filter(is_active=True),
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
