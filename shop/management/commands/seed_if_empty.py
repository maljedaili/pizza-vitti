from django.core.management import call_command
from django.core.management.base import BaseCommand
from shop.models import Category, Product


class Command(BaseCommand):
    help = 'Seed Pizza Vitti menu only when the menu database is empty.'

    def handle(self, *args, **kwargs):
        if Category.objects.exists() or Product.objects.exists():
            self.stdout.write('Menu data already exists; skipping seed_demo.')
            return
        self.stdout.write('No menu data found; running seed_demo.')
        call_command('seed_demo')
