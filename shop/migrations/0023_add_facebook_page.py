from django.db import migrations


FACEBOOK_URL = 'https://www.facebook.com/Pizza-vitti-235744923253527'


def add_facebook_page(apps, schema_editor):
    SiteConfiguration = apps.get_model('shop', 'SiteConfiguration')
    site, _ = SiteConfiguration.objects.get_or_create(pk=1)
    if not site.facebook_url:
        site.facebook_url = FACEBOOK_URL
        site.save(update_fields=['facebook_url'])


def remove_facebook_page(apps, schema_editor):
    SiteConfiguration = apps.get_model('shop', 'SiteConfiguration')
    SiteConfiguration.objects.filter(pk=1, facebook_url=FACEBOOK_URL).update(facebook_url='')


class Migration(migrations.Migration):
    dependencies = [('shop', '0022_publish_starter_blog_posts')]

    operations = [migrations.RunPython(add_facebook_page, remove_facebook_page)]
