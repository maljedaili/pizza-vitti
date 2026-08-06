from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

import requests
from django.core.management.base import BaseCommand, CommandError


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ''
        self.description = ''
        self.canonical = ''
        self.robots = ''
        self.h1_count = 0
        self.images = 0
        self.images_without_alt = 0
        self.images_without_size = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title':
            self._in_title = True
        elif tag == 'meta' and attrs.get('name', '').lower() == 'description':
            self.description = attrs.get('content', '').strip()
        elif tag == 'meta' and attrs.get('name', '').lower() == 'robots':
            self.robots = attrs.get('content', '').lower()
        elif tag == 'link' and attrs.get('rel', '').lower() == 'canonical':
            self.canonical = attrs.get('href', '').strip()
        elif tag == 'h1':
            self.h1_count += 1
        elif tag == 'img':
            self.images += 1
            if not attrs.get('alt', '').strip():
                self.images_without_alt += 1
            if not attrs.get('width') or not attrs.get('height'):
                self.images_without_size += 1

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()


def audit_url(url, timeout):
    try:
        response = requests.get(url, timeout=timeout, allow_redirects=False, headers={'User-Agent': 'PizzaVittiSEOAudit/1.0'})
    except requests.RequestException as exc:
        return {'url': url, 'error': str(exc)}
    result = {'url': url, 'status': response.status_code, 'redirect': response.headers.get('Location', '')}
    if response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
        parser = PageParser()
        parser.feed(response.text)
        result.update({
            'title': parser.title, 'description': parser.description,
            'canonical': parser.canonical, 'robots': parser.robots,
            'h1_count': parser.h1_count, 'images': parser.images,
            'images_without_alt': parser.images_without_alt,
            'images_without_size': parser.images_without_size,
        })
    return result


class Command(BaseCommand):
    help = 'Crawl sitemap URLs and report common technical SEO problems.'

    def add_arguments(self, parser):
        parser.add_argument('--base-url', default='https://pizza-vitti.kayen.fr')
        parser.add_argument('--limit', type=int, default=0, help='Maximum sitemap URLs to check; zero checks all.')
        parser.add_argument('--workers', type=int, default=8)
        parser.add_argument('--timeout', type=int, default=15)
        parser.add_argument('--details', action='store_true', help='Print representative URLs for each issue.')

    def handle(self, *args, **options):
        base_url = options['base_url'].rstrip('/')
        sitemap_url = base_url + '/sitemap.xml'
        try:
            response = requests.get(sitemap_url, timeout=options['timeout'], headers={'User-Agent': 'PizzaVittiSEOAudit/1.0'})
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
        except (requests.RequestException, ElementTree.ParseError) as exc:
            raise CommandError(f'Unable to read {sitemap_url}: {exc}') from exc
        urls = [element.text.strip() for element in root.iter() if element.tag.endswith('loc') and element.text]
        if options['limit']:
            urls = urls[:options['limit']]
        if not urls:
            raise CommandError('The sitemap contains no URLs.')

        results = []
        with ThreadPoolExecutor(max_workers=max(1, options['workers'])) as executor:
            futures = {executor.submit(audit_url, url, options['timeout']): url for url in urls}
            for future in as_completed(futures):
                results.append(future.result())

        issues = Counter()
        titles = Counter(result.get('title') for result in results if result.get('title'))
        descriptions = Counter(result.get('description') for result in results if result.get('description'))
        for result in results:
            if result.get('error'):
                issues['request errors'] += 1
                continue
            if result.get('status') != 200:
                issues['non-200 URLs'] += 1
                continue
            if result.get('redirect'):
                issues['redirects'] += 1
            if 'noindex' in result.get('robots', ''):
                issues['noindex URLs in sitemap'] += 1
            if not result.get('title'):
                issues['missing titles'] += 1
            if not result.get('description'):
                issues['missing descriptions'] += 1
            if result.get('h1_count') != 1:
                issues['pages without exactly one H1'] += 1
            if not result.get('canonical'):
                issues['missing canonicals'] += 1
            elif result['canonical'] != result['url']:
                issues['canonical mismatches'] += 1
            issues['images without alt'] += result.get('images_without_alt', 0)
            issues['images without dimensions'] += result.get('images_without_size', 0)
        issues['duplicate title values'] = sum(1 for count in titles.values() if count > 1)
        issues['duplicate description values'] = sum(1 for count in descriptions.values() if count > 1)

        self.stdout.write(f'Audited {len(results)} sitemap URLs from {sitemap_url}')
        for label in sorted(issues):
            self.stdout.write(f'{label}: {issues[label]}')
        if options['details']:
            duplicate_titles = {value for value, count in titles.items() if count > 1}
            duplicate_descriptions = {value for value, count in descriptions.items() if count > 1}
            detail_groups = {
                'Duplicate titles': [r['url'] for r in results if r.get('title') in duplicate_titles],
                'Duplicate descriptions': [r['url'] for r in results if r.get('description') in duplicate_descriptions],
                'Images without dimensions': [r['url'] for r in results if r.get('images_without_size', 0)],
                'Non-200 URLs': [r['url'] for r in results if r.get('status') != 200 or r.get('error')],
                'Canonical mismatches': [r['url'] for r in results if r.get('canonical') and r.get('canonical') != r['url']],
            }
            for heading, affected_urls in detail_groups.items():
                if affected_urls:
                    self.stdout.write(f'{heading} (first 10):')
                    for affected_url in sorted(affected_urls)[:10]:
                        self.stdout.write(f'  {affected_url}')
        if not any(issues.values()):
            self.stdout.write(self.style.SUCCESS('No audited SEO issues found.'))
