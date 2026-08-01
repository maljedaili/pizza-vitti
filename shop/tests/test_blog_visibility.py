from django.test import TestCase

from shop.models import BlogPost, SiteConfiguration


class BlogVisibilityTests(TestCase):
    def test_blog_navigation_is_visible_without_posts(self):
        response = self.client.get('/fr/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/fr/blog/"')

    def test_empty_blog_page_remains_available(self):
        BlogPost.objects.all().delete()
        response = self.client.get('/fr/blog/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'De nouveaux articles arrivent bientôt.')

    def test_blog_links_only_to_instagram(self):
        site = SiteConfiguration.load()
        site.instagram_url = 'https://www.instagram.com/pizza_vitti_bordeaux/'
        site.facebook_url = ''
        site.save(update_fields=['instagram_url', 'facebook_url'])

        response = self.client.get('/fr/blog/')

        self.assertContains(response, site.instagram_url)
        self.assertContains(response, '@pizzavitti.bordeaux')
        self.assertNotContains(response, 'facebook.com')

    def test_blog_interface_is_translated(self):
        english = self.client.get('/en/blog/')
        arabic = self.client.get('/ar/blog/')

        self.assertContains(english, 'Follow Pizza Vitti on Instagram')
        self.assertContains(english, 'Restaurant news')
        self.assertNotContains(english, 'Nouvelles du restaurant')
        self.assertContains(arabic, 'تابع Pizza Vitti على Instagram')
