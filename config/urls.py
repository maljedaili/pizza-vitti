from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from shop.sitemaps import ProductSitemap, BlogSitemap, StaticSitemap

sitemaps = {'static': StaticSitemap, 'products': ProductSitemap, 'blog': BlogSitemap}
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('robots.txt', include('shop.urls_robots')), 
    path('', include('shop.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
