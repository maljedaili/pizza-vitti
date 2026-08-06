from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class PrimaryDomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0].lower()
        if settings.REDIRECT_ALTERNATE_DOMAINS and host in settings.ALTERNATE_DOMAINS:
            target = f'{settings.PRIMARY_SCHEME}://{settings.PRIMARY_DOMAIN}{request.get_full_path()}'
            return HttpResponsePermanentRedirect(target)
        return self.get_response(request)


class PublicSecurityHeadersMiddleware:
    """Add browser protections that Django does not emit by default."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault('Permissions-Policy', settings.PERMISSIONS_POLICY)
        response.headers.setdefault('X-Permitted-Cross-Domain-Policies', 'none')
        return response
