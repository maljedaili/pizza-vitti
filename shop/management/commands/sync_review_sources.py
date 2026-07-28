from django.core.management.base import BaseCommand

from shop.models import Review


GOOGLE_REVIEWS_URL = 'https://www.google.com/search?q=pizza+vitti+-+ornano'


class Command(BaseCommand):
    help = 'Attach the verified Pizza Vitti Google Business Profile to Google reviews.'

    def handle(self, *args, **options):
        updated = Review.objects.filter(source__iexact='Google').update(
            source='Google',
            source_url=GOOGLE_REVIEWS_URL,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Linked {updated} Google review(s) to the verified business profile.'
        ))
