"""Publisher document extraction and public news-link normalization."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

ARTICLE_TYPES = {'article', 'newsarticle', 'blogposting', 'reportagenewsarticle', 'analysisnewsarticle', 'techarticle', 'scholarlyarticle'}
BLOCKED = re.compile(r'blocked by network security|verify (?:that )?you are human|checking your browser|enable javascript and cookies|access denied|just a moment', re.I)
PAYWALL = re.compile(r'subscribe to (?:continue|read|unlock)|sign in to (?:continue|read)|subscriber.only (?:content|article)|already a subscriber', re.I)
BODY_MARKER = re.compile(r'(?:^|[\s_-])(?:article[-_ ]*(?:body|content|text)|post[-_ ]*(?:body|content)|entry[-_ ]*content|story[-_ ]*(?:body|content)|body[-_ ]*copy)(?:$|[\s_-])', re.I)
JUNK_MARKER = re.compile(r'(?:^|[\s_-])(?:advertisement|advert|ads|related|recommended|newsletter|comments|cookie|share|sharing|social|breadcrumb)(?:$|[\s_-])', re.I)
VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


def clean_text(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def public_http_url(value):
    parsed = urlparse(str(value or ''))
    return bool(parsed.scheme in {'http', 'https'} and parsed.hostname and not parsed.username and not parsed.password)


def unwrap_news_url(url):
    """Decode public search redirect parameters without opening the aggregator."""
    for _ in range(3):
        parsed = urlparse(url)
        host = (parsed.hostname or '').lower()
        params = parse_qs(parsed.query)
        target = ''
        if host in {'bing.com', 'www.bing.com'} and parsed.path.lower().endswith('/apiclick.aspx'):
            target = params.get('url', [''])[0]
        elif host in {'duckduckgo.com', 'www.duckduckgo.com'}:
            target = params.get('uddg', [''])[0]
        if not public_http_url(target) or target == url:
            break
        url = target
    return url


def canonical_source_url(url):
    parsed = urlparse(unwrap_news_url(url))
    query = [(key, value) for key, values in parse_qs(parsed.query, keep_blank_values=True).items()
             if not key.lower().startswith('utm_') and key.lower() not in {'fbclid', 'gclid', 'at_medium', 'at_campaign'} for value in values]
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip('/') or '/', parsed.params, urlencode(query), ''))


@dataclass(frozen=True)
class ArticleDocument:
    text: str = ''
    kind: str = 'unavailable'
    title: str = ''
    published: str = ''
    canonical_url: str = ''
    note: str = ''


class PublisherHTML(HTMLParser):
    """Track nested article containers, metadata, and advertised RSS/Atom links."""
    def __init__(self, base_url=''):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.stack = []
        self.scopes = []
        self.page_parts = []
        self.jsonld = []
        self.script_parts = None
        self.metadata = {}
        self.feeds = []
        self.links = []
        self.title_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        tag = tag.lower()
        if tag == 'base' and public_http_url(urljoin(self.base_url, attrs.get('href', ''))):
            self.base_url = urljoin(self.base_url, attrs['href'])
        if tag == 'meta':
            key = (attrs.get('property') or attrs.get('name') or attrs.get('itemprop') or '').lower()
            self.metadata.setdefault(key, attrs.get('content', ''))
        if tag == 'link':
            link = urljoin(self.base_url, attrs.get('href', ''))
            rel = (attrs.get('rel') or '').lower().split()
            if public_http_url(link) and 'alternate' in rel and any(kind in attrs.get('type', '').lower() for kind in ('rss', 'atom')):
                if link not in self.feeds:
                    self.feeds.append(link)
            if 'canonical' in rel and public_http_url(link):
                self.metadata['canonical'] = link
        if tag == 'a' and attrs.get('href'):
            self.links.append(urljoin(self.base_url, attrs['href']))
        if tag == 'script' and 'ld+json' in attrs.get('type', '').lower():
            self.script_parts = []
        markers = ' '.join(attrs.get(key, '') for key in ('class', 'id'))
        skip = bool(self.stack and self.stack[-1]['skip']) or tag in {'script', 'style', 'nav', 'footer', 'aside', 'form', 'noscript', 'svg', 'button'} or bool(JUNK_MARKER.search(markers)) or attrs.get('aria-hidden') == 'true' or 'hidden' in attrs
        scope = None
        if not skip and (tag in {'article', 'main'} or 'articlebody' in attrs.get('itemprop', '').lower() or BODY_MARKER.search(markers)):
            scope = {'parts': [], 'specific': tag != 'main', 'depth': len(self.stack)}
            self.scopes.append(scope)
        if tag not in VOID_TAGS:
            self.stack.append({'tag': tag, 'skip': skip, 'scope': scope})
        elif tag in {'br', 'hr'} and not skip:
            self._append('\n')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'script' and self.script_parts is not None:
            self.jsonld.append(''.join(self.script_parts))
            self.script_parts = None
        if tag in {'p', 'div', 'section', 'h1', 'h2', 'h3', 'h4', 'li', 'blockquote', 'pre'}:
            self._append('\n')
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]['tag'] == tag:
                del self.stack[index:]
                break

    def _append(self, value):
        if self.stack and self.stack[-1]['skip']:
            return
        for entry in self.stack:
            if entry['scope'] is not None:
                entry['scope']['parts'].append(value)
        if any(entry['tag'] in {'p', 'h1', 'h2', 'h3', 'blockquote', 'li'} for entry in self.stack):
            self.page_parts.append(value)

    def handle_data(self, data):
        if self.script_parts is not None:
            self.script_parts.append(data)
            return
        if self.stack and self.stack[-1]['tag'] == 'title':
            self.title_parts.append(data)
        if data.strip():
            self._append(data)


def structured_articles(value):
    if isinstance(value, dict):
        types = value.get('@type', [])
        types = [types] if isinstance(types, str) else types
        if isinstance(types, list) and any(str(kind).lower().rsplit('/', 1)[-1] in ARTICLE_TYPES for kind in types):
            yield value
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from structured_articles(child)
    elif isinstance(value, list):
        for child in value:
            yield from structured_articles(child)


def paragraph_text(parts):
    lines = [clean_text(line) for line in ''.join(parts).splitlines()]
    return '\n\n'.join(line for line in lines if line)


def extract_document(html, base_url=''):
    parser = PublisherHTML(base_url)
    parser.feed(html)
    structured = []
    for raw in parser.jsonld:
        try:
            structured.extend(structured_articles(json.loads(raw)))
        except (ValueError, TypeError):
            pass
    title = clean_text(parser.metadata.get('og:title') or ''.join(parser.title_parts))
    canonical = parser.metadata.get('canonical') or parser.metadata.get('og:url') or ''
    published = parser.metadata.get('article:published_time') or parser.metadata.get('datepublished') or ''
    candidates = []
    restricted = False
    for article in structured:
        published = published or str(article.get('datePublished') or '')
        title = title or clean_text(article.get('headline'))
        restricted |= article.get('isAccessibleForFree') is False or article.get('isAccessibleForFree') == 'false'
        body = article.get('articleBody')
        if isinstance(body, str) and body.strip():
            if '<' in body:
                body_parser = PublisherHTML();body_parser.feed(body)
                body = paragraph_text(body_parser.page_parts) or clean_text(body)
            candidates.append((True, len(body), clean_text(body)))
    for scope in parser.scopes:
        text = paragraph_text(scope['parts'])
        if len(text) >= 180:
            candidates.append((scope['specific'], len(text), text))
    if candidates:
        specific, _, text = max(candidates, key=lambda candidate: (candidate[0], candidate[1]))
        kind = 'article' if specific else 'page'
    else:
        text, kind = paragraph_text(parser.page_parts), 'page'
    visible = ' '.join((title, text))
    if BLOCKED.search(visible[:1200]) and (len(text.split()) < 180 or not candidates):
        return ArticleDocument(title=title, note='Publisher returned an access challenge')
    note = ''
    if restricted or PAYWALL.search(visible):
        kind, note = 'partial', 'Only the publicly accessible publisher text was available'
    if len(text) < 180:
        kind = 'unavailable'
    return ArticleDocument(text=text, kind=kind, title=title, published=published,
                           canonical_url=canonical if public_http_url(canonical) else '', note=note)


def parse_google_news_resolution(body):
    """Read the URL from Google's public news-link RPC, ignoring other frames."""
    def frames(value):
        if not isinstance(value, list):
            return
        if len(value) >= 3 and value[:2] == ['wrb.fr', 'Fbv4je'] and isinstance(value[2], str):
            try:
                decoded = json.loads(value[2])
            except (ValueError, TypeError):
                return
            if isinstance(decoded, list) and len(decoded) >= 2 and decoded[0] == 'garturlres' and public_http_url(decoded[1]):
                yield decoded[1]
        else:
            for child in value:
                yield from frames(child)
    for line in body.splitlines():
        if not line.lstrip().startswith('['):
            continue
        try:
            matches = list(frames(json.loads(line)))
            if matches:
                return matches[0]
        except (ValueError, TypeError):
            continue
    return ''
