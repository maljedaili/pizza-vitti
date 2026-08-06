# Pizza Vitti SEO deployment

## Render environment

Set these values on the production web service:

```env
PRIMARY_DOMAIN=pizza-vitti.kayen.fr
PRIMARY_SCHEME=https
REDIRECT_ALTERNATE_DOMAINS=False
ALTERNATE_DOMAINS=
ENVIRONMENT=production
ALLOW_DEMO_DATA=False
GOOGLE_SITE_VERIFICATION=
BING_SITE_VERIFICATION=
GA4_MEASUREMENT_ID=
GOOGLE_TAG_MANAGER_ID=
MICROSOFT_CLARITY_ID=
```

Keep `REDIRECT_ALTERNATE_DOMAINS=False` until Pizza Vitti controls another official domain. A future domain change requires only updating `PRIMARY_DOMAIN`, adding the old host to `ALTERNATE_DOMAINS`, and then enabling the redirect.

The Render start script applies migrations and collects static files. It must never call `seed_demo` or `seed_if_empty` in production.

## Google Search Console

1. Add the URL-prefix property `https://pizza-vitti.kayen.fr/`.
2. Copy the HTML verification token into `GOOGLE_SITE_VERIFICATION` on Render.
3. Deploy, then verify ownership.
4. Submit `https://pizza-vitti.kayen.fr/sitemap.xml`.
5. Request indexing for the French homepage, menu, pizzas, main products, pastas, reservation, contact, reviews, blog, and the eight local pages.

## Google Business Profile

- Website: `https://pizza-vitti.kayen.fr/fr/`
- Menu: `https://pizza-vitti.kayen.fr/fr/menu/`
- Reservation: `https://pizza-vitti.kayen.fr/fr/reserver/`
- Order: use the direct takeaway menu or only verified partner URLs.
- Confirm that name, address, phone, hours, map URL, and social links match the website.

Run `python manage.py business_info_report` to print the canonical values for comparison with Google, TripAdvisor, PagesJaunes, Instagram, Uber Eats, Deliveroo, and Just Eat.

## Owner checks still required

- Enter the verified Google Business Profile URL in Site configuration.
- Enter only real Uber Eats, Deliveroo, and Just Eat URLs; empty links stay hidden.
- Confirm cuisine descriptions, accepted payments, coordinates, legal identity, and opening hours in Django admin.
- Review and edit every local landing page before changing its published status.
- Google review schema remains omitted unless the review source and displayed totals are verifiable.
