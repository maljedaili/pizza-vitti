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
        self.assertContains(response, 'Ajoutez vos articles depuis l’administration.')

    def test_blog_links_to_configured_social_profiles(self):
        site = SiteConfiguration.load()
        site.instagram_url = 'https://www.instagram.com/pizza_vitti_bordeaux/'
        site.facebook_url = 'https://www.facebook.com/Pizza-vitti-235744923253527'
        site.save(update_fields=['instagram_url', 'facebook_url'])

        response = self.client.get('/fr/blog/')

        self.assertContains(response, site.instagram_url)
        self.assertContains(response, site.facebook_url)
