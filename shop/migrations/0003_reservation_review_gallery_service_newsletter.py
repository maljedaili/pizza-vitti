from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shop', '0002_professionalclient_blogpost_external_image_and_more')]
    operations = [
        migrations.CreateModel(name='Reservation', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('name', models.CharField(max_length=140)), ('email', models.EmailField(max_length=254)), ('phone', models.CharField(blank=True, max_length=40)),
            ('date', models.DateField()), ('time', models.TimeField()), ('guests', models.PositiveIntegerField(default=2)), ('message', models.TextField(blank=True)),
            ('status', models.CharField(choices=[('new','Nouvelle'),('confirmed','Confirmée'),('cancelled','Annulée')], default='new', max_length=20)),
        ], options={'verbose_name':'Réservation','verbose_name_plural':'Réservations','ordering':['-date','-time']}),
        migrations.CreateModel(name='Review', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('name', models.CharField(max_length=120)), ('rating', models.PositiveSmallIntegerField(default=5)), ('comment', models.TextField(blank=True)), ('source', models.CharField(blank=True, max_length=80)),
            ('review_date', models.DateField(blank=True, null=True)), ('is_published', models.BooleanField(default=True)),
        ], options={'verbose_name':'Avis client','verbose_name_plural':'Avis clients','ordering':['-review_date','-created_at']}),
        migrations.CreateModel(name='GalleryImage', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('title', models.CharField(max_length=140)), ('image', models.ImageField(blank=True, null=True, upload_to='gallery/')), ('external_image', models.URLField(blank=True)),
            ('caption', models.CharField(blank=True, max_length=220)), ('order', models.PositiveIntegerField(default=0)), ('is_active', models.BooleanField(default=True)),
        ], options={'verbose_name':'Image galerie','verbose_name_plural':'Images galerie','ordering':['order','title']}),
        migrations.CreateModel(name='ServiceItem', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('title', models.CharField(max_length=160)), ('description', models.TextField()), ('icon', models.CharField(blank=True, help_text='Emoji ou petite icône', max_length=20)),
            ('order', models.PositiveIntegerField(default=0)), ('is_active', models.BooleanField(default=True)),
        ], options={'verbose_name':'Service','verbose_name_plural':'Services','ordering':['order','title']}),
        migrations.CreateModel(name='NewsletterSubscriber', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('email', models.EmailField(max_length=254, unique=True)), ('is_active', models.BooleanField(default=True)),
        ], options={'verbose_name':'Abonné newsletter','verbose_name_plural':'Abonnés newsletter','ordering':['-created_at']}),
    ]
