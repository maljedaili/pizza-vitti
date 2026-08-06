from shop.management.commands.seo_crawl_audit import PageParser
from django.test import SimpleTestCase


class SEOPageParserTests(SimpleTestCase):
    def test_parser_collects_core_page_signals(self):
        parser = PageParser()
        parser.feed('''<html><head><title>Pizza Vitti</title><meta name="description" content="Bordeaux pizza"><link rel="canonical" href="https://pizza-vitti.kayen.fr/fr/"></head><body><h1>Pizza Vitti</h1><img src="pizza.webp" alt="Pizza Regina" width="600" height="400"><img src="logo.png" alt=""></body></html>''')
        self.assertEqual(parser.title, 'Pizza Vitti')
        self.assertEqual(parser.description, 'Bordeaux pizza')
        self.assertEqual(parser.h1_count, 1)
        self.assertEqual(parser.images_without_alt, 1)
        self.assertEqual(parser.images_without_size, 1)
