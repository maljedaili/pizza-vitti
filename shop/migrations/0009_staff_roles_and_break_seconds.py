from django.db import migrations, models


def normalize_staff_roles(apps, schema_editor):
    StaffMember = apps.get_model('shop', 'StaffMember')
    role_map = {
        'cuisine': 'kitchen',
        'kitchen': 'kitchen',
        'salle': 'server',
        'serveur': 'server',
        'serveuse': 'server',
        'server': 'server',
        'cleaner': 'cleaner',
        'nettoyage': 'cleaner',
        'entretien': 'cleaner',
        'manager': 'manager',
        'responsable': 'manager',
    }
    for staff in StaffMember.objects.all():
        normalized = role_map.get((staff.role or '').strip().lower(), 'server')
        if staff.role != normalized:
            staff.role = normalized
            staff.save(update_fields=['role'])


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0008_operations_dashboards'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffshift',
            name='break_seconds',
            field=models.PositiveIntegerField(default=0, verbose_name='Pause cumulée (secondes)'),
        ),
        migrations.AlterField(
            model_name='staffmember',
            name='role',
            field=models.CharField(
                choices=[
                    ('kitchen', 'Cuisine'),
                    ('server', 'Serveur / Serveuse'),
                    ('cleaner', 'Entretien'),
                    ('manager', 'Responsable'),
                ],
                default='server',
                max_length=80,
            ),
        ),
        migrations.RunPython(normalize_staff_roles, migrations.RunPython.noop),
    ]
