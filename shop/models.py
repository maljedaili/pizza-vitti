from decimal import Decimal
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Category(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    def __str__(self): return self.name
    def get_absolute_url(self): return reverse('shop:category', args=[self.slug])

class Product(TimeStampedModel):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=210, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    unit = models.CharField(max_length=60, default='pièce')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    external_image = models.URLField(blank=True)
    badge = models.CharField(max_length=60, blank=True)
    stock = models.PositiveIntegerField(default=20)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False, verbose_name='Meilleure vente')
    is_pizza_of_month = models.BooleanField(default=False, verbose_name='Pizza du mois')
    professional_only = models.BooleanField(default=False, verbose_name='Réservé aux professionnels')
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    class Meta:
        ordering = ['-is_featured', 'name']
        verbose_name = 'Produit'
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    def __str__(self): return self.name
    @property
    def display_image(self): return self.image.url if self.image else self.external_image
    def get_absolute_url(self): return reverse('shop:product_detail', args=[self.slug])

class ProfessionalClient(TimeStampedModel):
    company_name = models.CharField(max_length=160, verbose_name='Entreprise')
    contact_name = models.CharField(max_length=160, blank=True, verbose_name='Contact')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=40, blank=True)
    password_hash = models.CharField(max_length=256, editable=False, blank=True)
    temporary_password = models.CharField(max_length=80, blank=True, help_text='Écrivez un nouveau mot de passe ici puis enregistrez. Il sera sécurisé automatiquement.')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    class Meta:
        ordering = ['company_name']
        verbose_name = 'Client professionnel'
        verbose_name_plural = 'Clients professionnels'
    def save(self, *args, **kwargs):
        if self.temporary_password:
            self.password_hash = make_password(self.temporary_password)
            self.temporary_password = ''
        super().save(*args, **kwargs)
    def check_password(self, raw_password):
        return bool(self.password_hash) and check_password(raw_password, self.password_hash)
    def __str__(self): return self.company_name

class BlogPost(TimeStampedModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    excerpt = models.CharField(max_length=220)
    body = models.TextField()
    image = models.ImageField(upload_to='blog/', blank=True, null=True)
    external_image = models.URLField(blank=True)
    is_published = models.BooleanField(default=True)
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Article de blog'
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    def __str__(self): return self.title
    @property
    def display_image(self): return self.image.url if self.image else self.external_image
    def get_absolute_url(self): return reverse('shop:blog_detail', args=[self.slug])

class CustomerMessage(TimeStampedModel):
    STATUS = [('new','Nouveau'),('read','Lu'),('archived','Archivé')]
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=160, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default='new')
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Message client'
    def __str__(self): return f'{self.name} - {self.subject or self.created_at:%d/%m/%Y}'

class Order(TimeStampedModel):
    CUSTOMER_TYPE = [('particulier','Particulier'),('professionnel','Professionnel')]
    STATUS = [
        ('received','Commande reçue'),('preparing','Préparation'),('ready','Prête'),('delivered','Livrée'),
        ('not_received','Client non livré / produit non reçu'),('refused','Produit refusé par le client'),
        ('cancelled','Annulée'),('refunded','Remboursée')]
    PAYMENT = [('pending','En attente'),('paid','Payée'),('failed','Échec'),('refunded','Remboursée'),('cash','Paiement livraison/retrait')]
    order_number = models.CharField(max_length=40, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE, default='particulier')
    professional_client = models.ForeignKey(ProfessionalClient, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    ORDER_TYPE = [('pickup','À emporter'),('dine_in','Sur place'),('uber_eats','Uber Eats'),('deliveroo','Deliveroo'),('just_eat','Just Eat')]
    table_number = models.CharField(max_length=20, blank=True, verbose_name='Numéro de table')
    address = models.TextField(blank=True)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE, default='pickup', verbose_name='Type de commande')
    selected_reward = models.CharField(max_length=80, blank=True, verbose_name='Cadeau fidélité choisi')
    promo_code = models.CharField(max_length=40, blank=True, verbose_name='Code promo')
    notes = models.TextField(blank=True)
    delivery_issue_note = models.TextField(blank=True, verbose_name='Note livraison/refus')
    status = models.CharField(max_length=20, choices=STATUS, default='received')
    payment_status = models.CharField(max_length=20, choices=PAYMENT, default='pending')
    stripe_session_id = models.CharField(max_length=255, blank=True)
    confirmation_email_sent = models.BooleanField(default=False, verbose_name='Email de confirmation envoyé')
    ready_email_sent = models.BooleanField(default=False, verbose_name='Email commande prête envoyé')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Commande'
    def __str__(self): return self.order_number
    def get_absolute_url(self): return reverse('shop:invoice', args=[self.order_number])

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=180)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self): return f'{self.quantity} × {self.name}'

class Reservation(TimeStampedModel):
    STATUS = [('new','Nouvelle'),('confirmed','Confirmée'),('cancelled','Annulée')]
    name = models.CharField(max_length=140)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    date = models.DateField()
    time = models.TimeField()
    guests = models.PositiveIntegerField(default=2)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='new')
    class Meta:
        ordering = ['-date','-time']
        verbose_name = 'Réservation'
        verbose_name_plural = 'Réservations'
    def __str__(self): return f'{self.name} - {self.date} {self.time}'

class Review(TimeStampedModel):
    name = models.CharField(max_length=120)
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(blank=True)
    source = models.CharField(max_length=80, blank=True)
    review_date = models.DateField(blank=True, null=True)
    is_published = models.BooleanField(default=True)
    class Meta:
        ordering = ['-review_date','-created_at']
        verbose_name = 'Avis client'
        verbose_name_plural = 'Avis clients'
    def __str__(self): return f'{self.name} - {self.rating}/5'

class GalleryImage(TimeStampedModel):
    title = models.CharField(max_length=140)
    image = models.ImageField(upload_to='gallery/', blank=True, null=True)
    external_image = models.URLField(blank=True)
    caption = models.CharField(max_length=220, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['order','title']
        verbose_name = 'Image galerie'
        verbose_name_plural = 'Images galerie'
    @property
    def display_image(self): return self.image.url if self.image else self.external_image
    def __str__(self): return self.title

class ServiceItem(TimeStampedModel):
    title = models.CharField(max_length=160)
    description = models.TextField()
    icon = models.CharField(max_length=20, blank=True, help_text='Emoji ou petite icône')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['order','title']
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
    def __str__(self): return self.title

class NewsletterSubscriber(TimeStampedModel):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Abonné newsletter'
        verbose_name_plural = 'Abonnés newsletter'
    def __str__(self): return self.email


class LoyaltyReward(TimeStampedModel):
    REWARD_TYPES = [
        ('free_pizza','Pizza offerte'),
        ('free_pasta','Pasta offerte'),
        ('free_dessert','Dessert offert'),
        ('discount_10','10% de réduction'),
    ]
    name = models.CharField(max_length=120, default='Cadeau fidélité')
    reward_type = models.CharField(max_length=30, choices=REWARD_TYPES, default='free_dessert')
    pizzas_required = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['pizzas_required','name']
        verbose_name = 'Récompense fidélité'
        verbose_name_plural = 'Récompenses fidélité'
    def __str__(self):
        return f'{self.name} - {self.get_reward_type_display()}'

class PromoCode(TimeStampedModel):
    code = models.CharField(max_length=40, unique=True)
    description = models.CharField(max_length=180, blank=True)
    discount_percent = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['code']
        verbose_name = 'Code promo'
        verbose_name_plural = 'Codes promo'
    def __str__(self):
        return f'{self.code} - {self.discount_percent}%'

class GiftCard(TimeStampedModel):
    code = models.CharField(max_length=40, unique=True)
    initial_value = models.DecimalField(max_digits=8, decimal_places=2, default=25)
    remaining_value = models.DecimalField(max_digits=8, decimal_places=2, default=25)
    recipient_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Carte cadeau'
        verbose_name_plural = 'Cartes cadeaux'
    def __str__(self):
        return f'{self.code} - {self.remaining_value} €'


class ProductTranslation(TimeStampedModel):
    LANGUAGES = [
        ('fr','Français'),('en','English'),('es','Español'),('it','Italiano'),('pt','Português'),
        ('nl','Nederlands'),('zh','中文'),('ja','日本語'),('ar','العربية'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='translations')
    language = models.CharField(max_length=5, choices=LANGUAGES)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    class Meta:
        unique_together = ('product', 'language')
        ordering = ['product__name', 'language']
        verbose_name = 'Traduction produit'
        verbose_name_plural = 'Traductions produits'
    def __str__(self):
        return f'{self.product.name} [{self.language}]'


class CategoryTranslation(TimeStampedModel):
    LANGUAGES = ProductTranslation.LANGUAGES
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='translations')
    language = models.CharField(max_length=5, choices=LANGUAGES)
    name = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    class Meta:
        unique_together = ('category', 'language')
        ordering = ['category__order', 'language']
        verbose_name = 'Traduction catégorie'
        verbose_name_plural = 'Traductions catégories'
    def __str__(self):
        return f'{self.category.name} [{self.language}]'


class Favorite(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pizza_vitti_favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')
    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']
        verbose_name = 'Favori client'
        verbose_name_plural = 'Favoris clients'
    def __str__(self):
        return f'{self.user} ❤ {self.product}'
