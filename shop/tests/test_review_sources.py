from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from shop.models import Review


class SyncReviewSourcesCommandTests(TestCase):
    def test_links_google_reviews_to_the_verified_business_profile(self):
        review = Review.objects.create(
            name='Client Google',
            rating=5,
            comment='Très bonne pizza.',
            source='Google',
        )

        call_command('sync_review_sources')

        review.refresh_from_db()
        self.assertEqual(
            review.source_url,
            'https://g.page/r/CZWvQ5cTiET3EAE/review',
        )
        response = self.client.get(reverse('shop:reviews'))
        self.assertContains(response, 'Client Google')
        self.assertContains(response, 'fiche Google de Pizza Vitti')

    def test_does_not_attribute_other_sources_to_google(self):
        review = Review.objects.create(
            name='Client Uniiti',
            rating=5,
            source='Uniiti',
        )

        call_command('sync_review_sources')

        review.refresh_from_db()
        self.assertEqual(review.source_url, '')

    def test_reviews_page_uses_the_verified_write_review_link(self):
        response = self.client.get('/fr/avis/')

        self.assertContains(response, 'https://g.page/r/CZWvQ5cTiET3EAE/review')
