from django.db import migrations


def remove_facebook_page(apps, schema_editor):
    SiteConfiguration = apps.get_model('shop', 'SiteConfiguration')
    SiteConfiguration.objects.exclude(facebook_url='').update(facebook_url='')


class Migration(migrations.Migration):
    dependencies = [('shop', '0024_add_instagram_page')]

    operations = [migrations.RunPython(remove_facebook_page, migrations.RunPython.noop)]
