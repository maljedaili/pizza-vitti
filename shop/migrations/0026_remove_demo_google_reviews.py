from django.db import migrations


DEMO_GOOGLE_REVIEWS = {
    'Marie': 'Très bonne pizza.',
    'Ahmed': 'Service rapide.',
    'Camille': 'Accueil chaleureux et vraie ambiance italienne.',
}
WRITE_REVIEW_URL = 'https://g.page/r/CZWvQ5cTiET3EAE/review'


def remove_demo_reviews_and_set_link(apps, schema_editor):
    Review = apps.get_model('shop', 'Review')
    SiteConfiguration = apps.get_model('shop', 'SiteConfiguration')
    for name, comment in DEMO_GOOGLE_REVIEWS.items():
        Review.objects.filter(
            name=name,
            comment=comment,
            source__iexact='Google',
            google_review_id__isnull=True,
        ).delete()
    SiteConfiguration.objects.update(google_review_url=WRITE_REVIEW_URL)


class Migration(migrations.Migration):
    dependencies = [('shop', '0025_remove_facebook_page')]

    operations = [migrations.RunPython(remove_demo_reviews_and_set_link, migrations.RunPython.noop)]
