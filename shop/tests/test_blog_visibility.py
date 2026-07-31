from django.test import TestCase

from shop.models import BlogPost


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
