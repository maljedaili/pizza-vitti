from django.contrib import admin
from django.utils.html import format_html
from .models import (
    BlogPost, CameraLocation, Category, CustomerMessage, DiningTable,
    ExceptionalClosure, GalleryImage, GiftCard, LoyaltyRedemption, LoyaltyReward,
    NewsletterSubscriber, OpeningPeriod, Order, OrderItem, Product, PromoCode,
    PurchaseOrder, PurchaseOrderItem, Reservation, Review, SecurityCamera,
    SiteConfiguration, StaffMember, StaffShift,
)

admin.site.site_header = "Pizza Vitti — Administration"
admin.site.site_title = "Pizza Vitti"
admin.site.index_title = "Gestion boutique, commandes, réservations et contenus"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('image_preview','name','order','is_active')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('order','is_active')
    search_fields = ('name',)
    readonly_fields = ('image_preview',)
    fieldsets = (
        ('Catégorie', {'fields': ('name','slug','description','order','is_active')}),
        ('Image', {'fields': ('image','static_image_path','image_preview')}),
    )

    @admin.display(description='Aperçu')
    def image_preview(self, obj):
        return format_html('<img src="{}" alt="" style="width:72px;height:48px;object-fit:cover;border-radius:6px">', obj.display_image) if obj and obj.display_image else '—'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name','category','price','unit','stock','is_available','is_best_seller','is_vegetarian','is_spicy','is_signature')
    list_filter = ('category','is_available','is_featured','is_best_seller','is_vegetarian','is_spicy','is_signature')
    list_editable = ('price','stock','is_available','is_best_seller','is_vegetarian','is_spicy','is_signature')
    search_fields = ('name','description')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Produit', {'fields': ('category','name','slug','description','allergens','price','unit','stock','badge')}),
        ('Vin (facultatif)', {'fields': ('glass_price','bottle_price','wine_colour','region','grape_variety','vintage')}),
        ('Images', {'fields': ('image','external_image')}),
        ('Badges', {'fields': ('is_vegetarian','is_spicy','is_signature')}),
        ('Publication', {'fields': ('is_available','is_featured','is_best_seller','is_pizza_of_month')}),
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
    list_display = ('order_number','customer_name','table_number','email','order_type','selected_reward','total','status','payment_status','confirmation_email_sent','ready_email_sent','created_at')
    list_filter = ('status','payment_status','order_type','confirmation_email_sent','ready_email_sent','created_at')
    search_fields = ('order_number','customer_name','email','phone','table_number')
    list_editable = ('status','payment_status')
    readonly_fields = ('order_number','stripe_session_id','confirmation_email_sent','ready_email_sent','created_at','updated_at')
    fieldsets = (
        ('Commande', {'fields': ('order_number','customer_name','email','phone','table_number','address','order_type','collection_date','collection_time','accepted_terms','selected_reward','promo_code','notes','total')}),
        ('Suivi', {'fields': ('status','payment_status','delivery_issue_note','confirmation_email_sent','ready_email_sent','stripe_session_id')}),
        ('Dates', {'fields': ('created_at','updated_at')}),
    )
    inlines = [OrderItemInline]


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('name','date','time','guests','phone','email','status','created_at')
    list_filter = ('status','date')
    search_fields = ('name','email','phone','message')
    list_editable = ('status',)


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Identité', {'fields': ('restaurant_name','hero_title','hero_description','address','telephone','public_email')}),
        ('Images de pages', {'fields': ('drinks_banner_image',)}),
        ('Liens', {'fields': ('google_maps_url','google_review_url','instagram_url','facebook_url','uber_eats_url','deliveroo_url','just_eat_url','google_play_url')}),
        ('Informations légales vérifiées', {'fields': ('legal_company_name','legal_form','legal_capital','legal_registration','legal_vat_number','legal_director','legal_host','legal_mediator')}),
    )

    def has_add_permission(self, request):
        return not SiteConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OpeningPeriod)
class OpeningPeriodAdmin(admin.ModelAdmin):
    list_display = ('weekday','opens_at','closes_at','is_active')
    list_filter = ('weekday','is_active')
    list_editable = ('opens_at','closes_at','is_active')


@admin.register(ExceptionalClosure)
class ExceptionalClosureAdmin(admin.ModelAdmin):
    list_display = ('date','is_closed','opens_at','closes_at','reason')
    list_filter = ('is_closed','date')
    list_editable = ('is_closed','opens_at','closes_at')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name','rating','source','review_date','is_published')
    list_filter = ('rating','source','is_published')
    list_editable = ('rating','is_published')
    search_fields = ('name','comment','source','source_url')
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


@admin.register(LoyaltyReward)
class LoyaltyRewardAdmin(admin.ModelAdmin):
    list_display = ('name','reward_type','pizzas_required','is_active','updated_at')
    list_editable = ('reward_type','pizzas_required','is_active')
    list_filter = ('reward_type','is_active')
    search_fields = ('name',)


@admin.register(LoyaltyRedemption)
class LoyaltyRedemptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'milestone', 'reward', 'order', 'created_at')
    list_filter = ('reward', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'order__order_number')
    readonly_fields = ('user', 'milestone', 'reward', 'order', 'created_at', 'updated_at')

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code','discount_percent','description','is_active','created_at')
    list_editable = ('discount_percent','is_active')
    list_filter = ('is_active',)
    search_fields = ('code','description')

@admin.register(GiftCard)
class GiftCardAdmin(admin.ModelAdmin):
    list_display = ('code','initial_value','remaining_value','recipient_email','is_active','created_at')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    search_fields = ('code','recipient_email')


@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = ('label','seats','x','y','is_active','updated_at')
    list_editable = ('seats','x','y','is_active')
    search_fields = ('label',)


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('name','username','role','is_active','updated_at')
    list_filter = ('is_active','role')
    list_editable = ('role','is_active')
    search_fields = ('name','username','role')
    readonly_fields = ('password_hash','created_at','updated_at')


@admin.register(StaffShift)
class StaffShiftAdmin(admin.ModelAdmin):
    list_display = ('staff','status','check_in_at','break_started_at','break_ended_at','break_seconds','check_out_at')
    list_filter = ('status','check_in_at')
    search_fields = ('staff__name','staff__username','notes')


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('supplier','reference','status','expected_date','received_date','total','created_at')
    list_filter = ('status','expected_date','received_date')
    list_editable = ('status','total')
    search_fields = ('supplier','reference','notes')
    inlines = [PurchaseOrderItemInline]


class SecurityCameraInline(admin.TabularInline):
    model = SecurityCamera
    extra = 0
    fields = ('name','stream_name','brand','supports_audio','supports_talk','sort_order','is_active')


@admin.register(CameraLocation)
class CameraLocationAdmin(admin.ModelAdmin):
    list_display = ('name','kind','gateway_url','is_active','updated_at')
    list_filter = ('kind','is_active')
    list_editable = ('is_active',)
    search_fields = ('name','address','gateway_url')
    inlines = [SecurityCameraInline]


@admin.register(SecurityCamera)
class SecurityCameraAdmin(admin.ModelAdmin):
    list_display = ('name','location','stream_name','brand','supports_audio','supports_talk','is_active')
    list_filter = ('location','supports_audio','supports_talk','is_active')
    list_editable = ('supports_audio','supports_talk','is_active')
    search_fields = ('name','stream_name','brand','model_name','location__name')

from .models import ProductTranslation, CategoryTranslation, Favorite

@admin.register(ProductTranslation)
class ProductTranslationAdmin(admin.ModelAdmin):
    list_display = ('product', 'language', 'name')
    list_filter = ('language',)
    search_fields = ('product__name', 'name', 'description')

@admin.register(CategoryTranslation)
class CategoryTranslationAdmin(admin.ModelAdmin):
    list_display = ('category', 'language', 'name')
    list_filter = ('language',)
    search_fields = ('category__name', 'name', 'description')

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__username', 'user__email', 'product__name')
