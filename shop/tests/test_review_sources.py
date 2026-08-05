from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings
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


@override_settings(
    GOOGLE_BUSINESS_ACCOUNT_ID='',
    GOOGLE_BUSINESS_LOCATION_ID='',
    GOOGLE_BUSINESS_CLIENT_ID='client-id',
    GOOGLE_BUSINESS_CLIENT_SECRET='client-secret',
    GOOGLE_BUSINESS_REFRESH_TOKEN='refresh-token',
)
class SyncGoogleReviewsCommandTests(TestCase):
    @patch('shop.management.commands.sync_google_reviews.requests.get')
    @patch('shop.management.commands.sync_google_reviews.requests.post')
    def test_discovers_pizza_vitti_location_and_imports_reviews(self, post, get):
        token_response = Mock()
        token_response.json.return_value = {'access_token': 'access-token'}
        token_response.raise_for_status.return_value = None
        post.return_value = token_response

        accounts_response = Mock()
        accounts_response.json.return_value = {
            'accounts': [{'name': 'accounts/123', 'accountName': 'Pizza Vitti'}],
        }
        accounts_response.raise_for_status.return_value = None
        locations_response = Mock()
        locations_response.json.return_value = {
            'locations': [{'name': 'locations/456', 'title': 'Pizza Vitti - Ornano'}],
        }
        locations_response.raise_for_status.return_value = None
        reviews_response = Mock()
        reviews_response.json.return_value = {
            'reviews': [{
                'reviewId': 'google-review-1',
                'reviewer': {
                    'displayName': 'Thomas',
                    'profilePhotoUrl': 'https://example.com/thomas.jpg',
                },
                'starRating': 'FIVE',
                'comment': 'Très bonne pizza.',
                'createTime': '2026-08-01T12:00:00Z',
                'updateTime': '2026-08-01T12:00:00Z',
            }],
        }
        reviews_response.raise_for_status.return_value = None
        get.side_effect = [accounts_response, locations_response, reviews_response]

        output = StringIO()
        call_command('sync_google_reviews', stdout=output)

        review = Review.objects.get(google_review_id='google-review-1')
        self.assertEqual(review.name, 'Thomas')
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.reviewer_photo_url, 'https://example.com/thomas.jpg')
        self.assertIn('Google location detected: Pizza Vitti - Ornano.', output.getvalue())
        self.assertIn('Google reviews synchronized: 1 created, 0 updated.', output.getvalue())
