from django.db import migrations


INSTAGRAM_URL = 'https://www.instagram.com/pizzavitti.bordeaux/'


def add_instagram_page(apps, schema_editor):
    SiteConfiguration = apps.get_model('shop', 'SiteConfiguration')
    site, _ = SiteConfiguration.objects.get_or_create(pk=1)
    if not site.instagram_url:
        site.instagram_url = INSTAGRAM_URL
        site.save(update_fields=['instagram_url'])


def remove_instagram_page(apps, schema_editor):
    SiteConfiguration = apps.get_model('shop', 'SiteConfiguration')
    SiteConfiguration.objects.filter(pk=1, instagram_url=INSTAGRAM_URL).update(instagram_url='')


class Migration(migrations.Migration):
    dependencies = [('shop', '0023_add_facebook_page')]

    operations = [migrations.RunPython(add_instagram_page, remove_instagram_page)]
