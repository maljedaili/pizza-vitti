from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from shop.sitemaps import ProductSitemap, BlogSitemap, StaticSitemap
from shop import views as shop_views

sitemaps = {'static': StaticSitemap, 'products': ProductSitemap, 'blog': BlogSitemap}
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('robots.txt', include('shop.urls_robots')), 
    path('.well-known/assetlinks.json', shop_views.android_asset_links, name='android_asset_links'),
    path('manifest.webmanifest', shop_views.manifest_webmanifest, name='manifest_webmanifest'),
    path('sw.js', shop_views.service_worker, name='service_worker'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('', include('shop.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
