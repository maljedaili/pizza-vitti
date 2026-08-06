from urllib.parse import urlsplit, urlunsplit

from django.conf import settings


def public_origin(request=None):
    """Return the configured production origin, with a local-test escape hatch."""
    if request:
        host = request.get_host().split(':')[0]
        if host == 'testserver' or (settings.DEBUG and host in {'localhost', '127.0.0.1'}):
            return f'{request.scheme}://{request.get_host()}'
    return settings.PUBLIC_SITE_URL.rstrip('/')


def absolute_public_url(path='/', request=None):
    if not path:
        path = '/'
    parts = urlsplit(path)
    clean_path = parts.path or '/'
    if not clean_path.startswith('/'):
        clean_path = '/' + clean_path
    origin = urlsplit(public_origin(request))
    return urlunsplit((origin.scheme, origin.netloc, clean_path, '', ''))
