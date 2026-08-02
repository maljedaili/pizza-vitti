from types import SimpleNamespace
from urllib.parse import urlsplit

from django.conf import settings
from django.template.response import TemplateResponse


def configured_sitemap(request, sitemaps):
    """Render sitemap URLs with the public SITE_URL instead of django_site."""
    configured = urlsplit(settings.SITE_URL)
    use_request_host = configured.hostname in {None, 'localhost', '127.0.0.1'}
    domain = request.get_host() if use_request_host else configured.netloc
    protocol = request.scheme if use_request_host else configured.scheme or request.scheme
    site = SimpleNamespace(domain=domain)
    page = request.GET.get('p', 1)
    urls = []
    for sitemap_class in sitemaps.values():
        sitemap = sitemap_class() if callable(sitemap_class) else sitemap_class
        urls.extend(sitemap.get_urls(page=page, site=site, protocol=protocol))
    return TemplateResponse(
        request,
        'sitemap.xml',
        {'urlset': urls},
        content_type='application/xml',
    )
