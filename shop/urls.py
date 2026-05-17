from django.urls import path
from . import views
app_name = 'shop'
urlpatterns = [
    path('', views.home, name='home'),
    path('a-propos/', views.about, name='about'),
    path('faq/', views.faq, name='faq'),
    path('boutique/', views.boutique, name='boutique'),
    path('reservation/', views.booking, name='booking'),
    path('avis/', views.reviews, name='reviews'),
    path('galerie/', views.gallery, name='gallery'),
    path('boutique/categorie/<slug:slug>/', views.category, name='category'),
    path('produit/<slug:slug>/', views.product_detail, name='product_detail'),
    path('panier/', views.cart, name='cart'),
    path('panier/ajouter/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('panier/maj/', views.update_cart, name='update_cart'),
    path('panier/retirer/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('commande/', views.checkout, name='checkout'),
    path('paiement/stripe/<int:order_id>/', views.create_checkout_session, name='stripe_checkout'),
    path('paiement/succes/<str:order_number>/', views.payment_success, name='payment_success'),
    path('facture/<str:order_number>/', views.invoice, name='invoice'),
    path('facture/<str:order_number>/signaler/', views.report_order_issue, name='report_order_issue'),
    path('suivi-commande/', views.track_order, name='track_order'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('contact/', views.contact, name='contact'),
    path('bot/reponse/', views.bot_reply, name='bot_reply'),
    path('newsletter/', views.newsletter, name='newsletter'),
    path('mentions-legales/', views.simple_page, {'title':'Mentions légales'}, name='mentions'),
    path('legal-notice/', views.simple_page, {'title':'Legal Notice'}, name='legal_notice'),
    path('cgv/', views.simple_page, {'title':'Conditions générales de vente'}, name='cgv'),
   
]
