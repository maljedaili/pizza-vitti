from django.conf import settings
from django.core.management.base import BaseCommand

from shop.models import SiteConfiguration
from shop.seo import absolute_public_url
from shop.translations import localized_url


class Command(BaseCommand):
    help = 'Print the canonical Pizza Vitti business information for external listing checks.'

    def handle(self, *args, **options):
        site = SiteConfiguration.load()
        rows = (
            ('Name', site.restaurant_name),
            ('Address', site.address),
            ('Phone', site.telephone),
            ('Email', site.public_email or settings.RESERVATION_EMAIL),
            ('Website', absolute_public_url(localized_url('home', 'fr'))),
            ('Menu', absolute_public_url(localized_url('menu', 'fr'))),
            ('Reservation', absolute_public_url(localized_url('booking', 'fr'))),
            ('Google Maps', site.google_maps_url),
        )
        for label, value in rows:
            self.stdout.write(f'{label}: {value}')
