from django.core.management import call_command
from django.core.management.base import BaseCommand
from shop.models import Category, Product
from django.conf import settings
from django.core.management.base import CommandError


class Command(BaseCommand):
    help = 'Seed Pizza Vitti menu only when the menu database is empty.'

    def handle(self, *args, **kwargs):
        if Category.objects.exists() or Product.objects.exists():
            self.stdout.write('Menu data already exists; skipping seed_demo.')
            return
        if settings.ENVIRONMENT == 'production' and not settings.ALLOW_DEMO_DATA:
            raise CommandError('Demo data is disabled in production. Set ALLOW_DEMO_DATA=True only for an intentional one-off run.')
        self.stdout.write('No menu data found; running seed_demo.')
        call_command('seed_demo')
