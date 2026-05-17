from django.contrib import admin
from .models import Category, Product, BlogPost, CustomerMessage, Order, OrderItem, Reservation, Review, GalleryImage, NewsletterSubscriber

admin.site.site_header = "Pizza Vitti — Administration"
admin.site.site_title = "Pizza Vitti"
admin.site.index_title = "Gestion boutique, commandes, réservations et contenus"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name','order','is_active')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('order','is_active')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name','category','price','unit','stock','is_available','is_featured')
    list_filter = ('category','is_available','is_featured')
    list_editable = ('price','stock','is_available','is_featured')
    search_fields = ('name','description')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Produit', {'fields': ('category','name','slug','description','price','unit','stock','badge')}),
        ('Images', {'fields': ('image','external_image')}),
        ('Publication', {'fields': ('is_available','is_featured')}),
        ('SEO', {'fields': ('meta_title','meta_description')}),
    )

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title','is_published','created_at')
    list_filter = ('is_published',)
    search_fields = ('title','body')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(CustomerMessage)
class CustomerMessageAdmin(admin.ModelAdmin):
    list_display = ('name','email','phone','subject','status','created_at')
    list_filter = ('status','created_at')
    search_fields = ('name','email','phone','message')
    list_editable = ('status',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('name','quantity','unit_price','line_total')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number','customer_name','email','total','status','payment_status','created_at')
    list_filter = ('status','payment_status','created_at')
    search_fields = ('order_number','customer_name','email','phone')
    list_editable = ('status','payment_status')
    readonly_fields = ('order_number','stripe_session_id','created_at','updated_at')
    fieldsets = (
        ('Commande', {'fields': ('order_number','customer_name','email','phone','address','notes','total')}),
        ('Suivi', {'fields': ('status','payment_status','delivery_issue_note','stripe_session_id')}),
        ('Dates', {'fields': ('created_at','updated_at')}),
    )
    inlines = [OrderItemInline]


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('name','date','time','guests','phone','email','status','created_at')
    list_filter = ('status','date')
    search_fields = ('name','email','phone','message')
    list_editable = ('status',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name','rating','source','review_date','is_published')
    list_filter = ('rating','source','is_published')
    list_editable = ('rating','is_published')
    search_fields = ('name','comment','source')
    actions = ('publish_reviews','hide_reviews')

    @admin.action(description='Afficher les avis sélectionnés')
    def publish_reviews(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description='Masquer les avis sélectionnés')
    def hide_reviews(self, request, queryset):
        queryset.update(is_published=False)

@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('title','order','is_active','updated_at')
    list_editable = ('order','is_active')
    search_fields = ('title','caption')

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email','is_active','created_at')
    list_filter = ('is_active',)
    search_fields = ('email',)
