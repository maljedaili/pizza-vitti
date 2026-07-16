from django.contrib import admin
from .models import Category, Product, BlogPost, CustomerMessage, Order, OrderItem, Reservation, Review, GalleryImage, NewsletterSubscriber, LoyaltyReward, PromoCode, GiftCard, DiningTable, StaffMember, StaffShift, PurchaseOrder, PurchaseOrderItem

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
    list_display = ('name','category','price','unit','stock','is_available','is_featured','is_best_seller','is_pizza_of_month')
    list_filter = ('category','is_available','is_featured','is_best_seller','is_pizza_of_month')
    list_editable = ('price','stock','is_available','is_featured','is_best_seller','is_pizza_of_month')
    search_fields = ('name','description')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Produit', {'fields': ('category','name','slug','description','price','unit','stock','badge')}),
        ('Images', {'fields': ('image','external_image')}),
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
        ('Commande', {'fields': ('order_number','customer_name','email','phone','table_number','address','order_type','selected_reward','promo_code','notes','total')}),
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


@admin.register(LoyaltyReward)
class LoyaltyRewardAdmin(admin.ModelAdmin):
    list_display = ('name','reward_type','pizzas_required','is_active','updated_at')
    list_editable = ('reward_type','pizzas_required','is_active')
    list_filter = ('reward_type','is_active')
    search_fields = ('name',)

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
    list_display = ('staff','status','check_in_at','break_started_at','break_ended_at','check_out_at')
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
