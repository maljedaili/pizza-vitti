import requests

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime

from shop.models import Review


TOKEN_URL = 'https://oauth2.googleapis.com/token'
REVIEWS_URL = 'https://mybusiness.googleapis.com/v4/accounts/{account}/locations/{location}/reviews'
STAR_VALUES = {
    'ONE': 1,
    'TWO': 2,
    'THREE': 3,
    'FOUR': 4,
    'FIVE': 5,
}


class Command(BaseCommand):
    help = 'Synchronise verified Google Business Profile reviews with the website.'

    def _configuration(self):
        values = {
            'account': settings.GOOGLE_BUSINESS_ACCOUNT_ID,
            'location': settings.GOOGLE_BUSINESS_LOCATION_ID,
            'client_id': settings.GOOGLE_BUSINESS_CLIENT_ID,
            'client_secret': settings.GOOGLE_BUSINESS_CLIENT_SECRET,
            'refresh_token': settings.GOOGLE_BUSINESS_REFRESH_TOKEN,
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            names = ', '.join(f'GOOGLE_BUSINESS_{name.upper()}' for name in missing)
            raise CommandError(f'Missing configuration: {names}')
        return values

    def _access_token(self, config):
        response = requests.post(
            TOKEN_URL,
            data={
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'refresh_token': config['refresh_token'],
                'grant_type': 'refresh_token',
            },
            timeout=20,
        )
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError('Google OAuth token refresh failed.') from exc
        token = response.json().get('access_token')
        if not token:
            raise CommandError('Google OAuth did not return an access token.')
        return token

    def handle(self, *args, **options):
        config = self._configuration()
        token = self._access_token(config)
        url = REVIEWS_URL.format(account=config['account'], location=config['location'])
        headers = {'Authorization': f'Bearer {token}'}
        page_token = None
        created = updated = 0

        while True:
            params = {'pageSize': 50, 'orderBy': 'updateTime desc'}
            if page_token:
                params['pageToken'] = page_token
            response = requests.get(url, headers=headers, params=params, timeout=30)
            try:
                response.raise_for_status()
            except requests.RequestException as exc:
                raise CommandError('Google Business Profile review download failed.') from exc

            payload = response.json()
            for item in payload.get('reviews', []):
                reviewer = item.get('reviewer') or {}
                updated_at = parse_datetime(item.get('updateTime') or '')
                review_date = parse_datetime(item.get('createTime') or '')
                _, was_created = Review.objects.update_or_create(
                    google_review_id=item.get('reviewId') or item.get('name'),
                    defaults={
                        'name': reviewer.get('displayName') or 'Utilisateur Google',
                        'reviewer_photo_url': reviewer.get('profilePhotoUrl') or '',
                        'rating': STAR_VALUES.get(item.get('starRating'), 5),
                        'comment': item.get('comment') or '',
                        'source': 'Google',
                        'source_url': settings.GOOGLE_REVIEW_URL,
                        'review_date': review_date.date() if review_date else None,
                        'google_updated_at': updated_at,
                        'is_published': True,
                    },
                )
                created += int(was_created)
                updated += int(not was_created)

            page_token = payload.get('nextPageToken')
            if not page_token:
                break

        self.stdout.write(self.style.SUCCESS(
            f'Google reviews synchronized: {created} created, {updated} updated.'
        ))
