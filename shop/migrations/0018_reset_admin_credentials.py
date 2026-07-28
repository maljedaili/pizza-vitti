from django.db import migrations


ADMIN_PASSWORD_HASH = (
    'pbkdf2_sha256$870000$dTkaksTysOVRzFY05nm1Th$'
    'QuAH796QmbGEdvHTBcMOMsvlfbk/SakqIDR0R3OeacI='
)


def reset_admin_credentials(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    user, _ = User.objects.get_or_create(username='admin')
    user.password = ADMIN_PASSWORD_HASH
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=['password', 'is_active', 'is_staff', 'is_superuser'])


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0017_siteconfiguration_antipasti_banner_image_and_more'),
    ]

    operations = [
        migrations.RunPython(reset_admin_credentials, migrations.RunPython.noop),
    ]
