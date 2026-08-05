import requests

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime

from shop.models import Review


TOKEN_URL = 'https://oauth2.googleapis.com/token'
ACCOUNTS_URL = 'https://mybusinessaccountmanagement.googleapis.com/v1/accounts'
LOCATIONS_URL = 'https://mybusinessbusinessinformation.googleapis.com/v1/{account}/locations'
LEGACY_ACCOUNTS_URL = 'https://mybusiness.googleapis.com/v4/accounts'
LEGACY_LOCATIONS_URL = 'https://mybusiness.googleapis.com/v4/{account}/locations'
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
        missing = [
            name for name in ('client_id', 'client_secret', 'refresh_token')
            if not values[name]
        ]
        if missing:
            names = ', '.join(f'GOOGLE_BUSINESS_{name.upper()}' for name in missing)
            raise CommandError(f'Missing configuration: {names}')
        return values

    def _resource_ids(self, config, headers):
        if config['account'] and config['location']:
            return (
                config['account'].split('/')[-1],
                config['location'].split('/')[-1],
            )

        response = requests.get(ACCOUNTS_URL, headers=headers, timeout=30)
        try:
            response.raise_for_status()
        except requests.RequestException:
            response = requests.get(LEGACY_ACCOUNTS_URL, headers=headers, timeout=30)
            try:
                response.raise_for_status()
            except requests.RequestException as exc:
                raise CommandError('Google Business Profile account discovery failed.') from exc

        accounts = response.json().get('accounts', [])
        if not accounts:
            raise CommandError('No Google Business Profile account is available for this login.')

        candidates = []
        for account in accounts:
            account_name = account.get('name', '')
            if not account_name:
                continue
            response = requests.get(
                LOCATIONS_URL.format(account=account_name),
                headers=headers,
                params={'readMask': 'name,title,storeCode', 'pageSize': 100},
                timeout=30,
            )
            try:
                response.raise_for_status()
            except requests.RequestException:
                response = requests.get(
                    LEGACY_LOCATIONS_URL.format(account=account_name),
                    headers=headers,
                    params={'pageSize': 100},
                    timeout=30,
                )
                try:
                    response.raise_for_status()
                except requests.RequestException:
                    continue
            for location in response.json().get('locations', []):
                location_name = location.get('name', '')
                if location_name:
                    candidates.append((account_name, location_name, location.get('title', '')))

        pizza_vitti = [row for row in candidates if 'pizza vitti' in row[2].lower()]
        matches = pizza_vitti or candidates
        if len(matches) != 1:
            raise CommandError(
                'Unable to identify one Pizza Vitti location automatically. '
                'Set GOOGLE_BUSINESS_ACCOUNT_ID and GOOGLE_BUSINESS_LOCATION_ID in Render.'
            )

        account_name, location_name, title = matches[0]
        self.stdout.write(f'Google location detected: {title or location_name}.')
        return account_name.split('/')[-1], location_name.split('/')[-1]

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
        headers = {'Authorization': f'Bearer {token}'}
        account_id, location_id = self._resource_ids(config, headers)
        url = REVIEWS_URL.format(account=account_id, location=location_id)
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
