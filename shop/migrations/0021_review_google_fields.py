from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shop', '0020_product_availability_status')]

    operations = [
        migrations.AddField(
            model_name='review',
            name='google_review_id',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='review',
            name='google_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='review',
            name='reviewer_photo_url',
            field=models.URLField(blank=True),
        ),
    ]
