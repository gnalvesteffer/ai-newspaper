"""Offline regressions for public-source discovery and article extraction."""
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import server
from article_reader import extract_document, canonical_source_url, parse_google_news_resolution, PublisherHTML

BODY = 'Researchers published detailed findings about safer batteries and explained their experimental methods. ' * 12


class ExtractionTests(unittest.TestCase):
    def test_nested_article_ignores_navigation_and_related(self):
        doc = extract_document(f'<nav><p>Navigation junk</p></nav><main><div class="article__body"><h1>Battery findings</h1><p>{BODY}</p><aside><p>Buy now</p></aside><div class="related"><p>Unrelated story</p></div></div></main>')
        self.assertEqual(doc.kind, 'article')
        self.assertIn(BODY.strip(), doc.text)
        for junk in ['Navigation junk', 'Buy now', 'Unrelated story']:
            self.assertNotIn(junk, doc.text)

    def test_main_is_not_misreported_as_full_article(self):
        self.assertEqual(extract_document(f'<main><p>{BODY}</p></main>').kind, 'page')

    def test_structured_article_and_date(self):
        raw = json.dumps({'@graph': [{'@type': 'NewsArticle', 'articleBody': BODY, 'datePublished': '2026-10-02', 'headline': 'Battery study'}]})
        doc = extract_document(f'<script type="application/ld+json">{raw}</script>')
        self.assertEqual(doc.kind, 'article')
        self.assertEqual(doc.published, '2026-10-02')
        self.assertEqual(doc.title, 'Battery study')

    def test_webpage_schema_does_not_count_as_article(self):
        raw = json.dumps({'@type': 'WebPage', 'articleBody': BODY})
        self.assertEqual(extract_document(f'<script type="application/ld+json">{raw}</script>').kind, 'unavailable')

    def test_challenge_and_paywall(self):
        self.assertEqual(extract_document('<title>Just a moment</title><main><p>Verify you are human</p></main>').kind, 'unavailable')
        self.assertEqual(extract_document(f'<article><p>{BODY}</p><p>Subscribe to continue</p></article>').kind, 'partial')

    def test_advertised_feed_resolves_relative_link(self):
        parser = PublisherHTML('https://publisher.test/news/')
        parser.feed('<link rel="alternate" type="application/atom+xml" href="/feed.xml">')
        self.assertEqual(parser.feeds, ['https://publisher.test/feed.xml'])


class SourceTests(unittest.TestCase):
    def setUp(self):
        server.SOURCE_CACHE.clear()

    def test_feed_preserves_publisher_body_and_missing_date(self):
        xml = f'<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><title>News</title><item><title>Study</title><link>https://news.google.com/rss/articles/id</link><source url="https://publisher.test">Publisher</source><description>Short snippet</description><content:encoded><![CDATA[<p>{BODY}</p>]]></content:encoded></item></channel></rss>'
        row = server.parse_feed(xml, {'name': 'Google News', 'weight': 5})[0]
        self.assertEqual(row['published'], '')
        self.assertEqual(row['publisher_url'], 'https://publisher.test')
        self.assertIn(BODY.strip(), row['feed_content'])

    def test_atom_alternate_relative_link(self):
        xml = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Study</title><link rel="self" href="/api/1"/><link rel="alternate" href="/story"/><content>Body</content></entry></feed>'
        row = server.parse_feed(xml, {'name': 'Publisher', 'url': 'https://publisher.test/feed', 'weight': 6})[0]
        self.assertEqual(row['link'], 'https://publisher.test/story')

    def test_redirect_and_tracking_normalization(self):
        url = 'https://www.bing.com/news/apiclick.aspx?url=https%3A%2F%2Fpublisher.test%2FStory%3Futm_source%3Dx%26id%3D1'
        self.assertEqual(canonical_source_url(url), 'https://publisher.test/Story?id=1')
        self.assertNotEqual(canonical_source_url('https://publisher.test/Story'), canonical_source_url('https://publisher.test/story'))

    def test_rpc_parse_only_expected_frame(self):
        frame = [['wrb.fr', 'Fbv4je', json.dumps(['garturlres', 'https://publisher.test/story', 1])]]
        self.assertEqual(parse_google_news_resolution(")]}'\n\n123\n" + json.dumps(frame)), 'https://publisher.test/story')
        for body in ['invalid', '[["wrb.fr","other","https://publisher.test"]]', json.dumps([['wrb.fr', 'Fbv4je', json.dumps(['garturlres', 'javascript:alert(1)'])]])]:
            self.assertEqual(parse_google_news_resolution(body), '')

    def test_google_signed_resolution(self):
        row = {'link': 'https://news.google.com/rss/articles/opaque', 'title': 'Study', 'publisher': 'Publisher'}
        html = b'<div data-n-a-sg="signed" data-n-a-ts="123"></div>'
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps([['wrb.fr', 'Fbv4je', json.dumps(['garturlres', 'https://publisher.test/story'])]]).encode()
        with patch.object(server, 'fetch_bytes', return_value=(html, 'text/html', row['link'], 'utf-8')), patch.object(server, 'urlopen', return_value=response) as opening:
            self.assertEqual(server.resolve_publisher_url(row), 'https://publisher.test/story')
            self.assertIn('garturlreq', opening.call_args.args[0].data.decode())

    def test_article_reads_publisher_without_browser(self):
        row = {'link': 'https://news.google.com/rss/articles/id', 'title': 'Study', 'publisher': 'Publisher', 'excerpt': 'Tiny excerpt'}
        with patch.object(server, 'resolve_publisher_url', return_value='https://publisher.test/story'), patch.object(server, 'fetch_bytes', return_value=(f'<article><p>{BODY}</p></article>'.encode(), 'text/html', 'https://publisher.test/story', 'utf-8')) as fetch, patch.object(server, 'playwright_article_html') as browser:
            server.article_text(row)
        self.assertEqual(fetch.call_args.args[0], 'https://publisher.test/story')
        browser.assert_not_called()
        self.assertEqual(row['read_kind'], 'article')
        self.assertEqual(row['article_url'], 'https://publisher.test/story')
        self.assertGreater(row['source_chars'], 500)

    def test_short_article_is_partial_not_full(self):
        row = {'link': 'https://publisher.test/story', 'title': 'Study', 'publisher': 'Publisher', 'excerpt': 'Snippet'}
        html = '<article><p>' + BODY[:300] + '</p></article>'
        with patch.object(server, 'fetch_bytes', return_value=(html.encode(), 'text/html', row['link'], 'utf-8')), patch.object(server, 'playwright_article_html', return_value=(html, row['link'])), patch.object(server, 'jina_reader_text', return_value=''):
            server.article_text(row)
        self.assertEqual(row['read_kind'], 'partial')
        self.assertIn('Partial article text', row['read_status'])

    def test_cache_returns_copies(self):
        first = server.cached_source('test', lambda: [{'title': 'Original'}])
        first[0]['title'] = 'Mutated'
        self.assertEqual(server.cached_source('test', lambda: []), [{'title': 'Original'}])

    def test_fulltext_relevance_requires_literal_evidence(self):
        row = {'title': 'Study', 'publisher': 'Publisher', 'published': '', 'feed': 'RSS', 'read_status': 'Full article read', 'article_url': 'https://publisher.test/story', 'article_text': BODY}
        for evidence, expected in [('Invented geographic connection', 0), (BODY[:40], 1)]:
            response = {'summaries': [{'id': '0', 'relevant': True, 'relevance_evidence': evidence, 'headline': 'Study'}]}
            with patch.object(server, 'call_model_json', return_value=response):
                result = server.summarize_batch({}, [(0, dict(row))], 'batteries')
            self.assertEqual(len(result), expected)

    def test_model_scoped_location_needs_source_evidence(self):
        row = {'title': 'Study', 'publisher': 'Local newspaper', 'published': '', 'feed': 'RSS', 'read_status': 'Full article read', 'article_url': 'https://publisher.test/story', 'article_text': BODY}
        response = {'summaries': [{'id': '0', 'relevant': True, 'relevance_evidence': BODY[:40], 'headline': 'Study'}]}
        with patch.object(server, 'call_model_json', return_value=response):
            self.assertEqual(server.summarize_batch({'_required_locations': ['Killeen']}, [(0, row)], 'Killeen research'), [])

    def test_small_context_summary_preserves_stored_source(self):
        row = {'title': 'Study', 'publisher': 'Publisher', 'published': '', 'feed': 'RSS', 'read_status': 'Full article read', 'article_url': 'https://publisher.test/story', 'article_text': BODY * 20}
        with patch.object(server, 'call_model_json', return_value={'summaries': []}) as model:
            server.summarize_batch({'contextLength': 4096, 'outputTokens': 1024}, [(0, row)], 'batteries')
        content = model.call_args.args[1][1]['content']
        self.assertLess(len(content), 6000)
        self.assertEqual(row['article_text'], BODY * 20)


class ResearchRoundTests(unittest.TestCase):
    def test_bounded_followup_uses_model_queries(self):
        current = datetime.now(timezone.utc).isoformat()
        row = {'title': 'New battery chemistry', 'link': 'https://publisher.test/story', 'publisher': 'Publisher', 'published': current, 'excerpt': BODY, 'weight': 5}
        plans = [{'queries': ['battery durability study', 'battery recycling research']}]
        seen_queries = []
        def news(query, *args, **kwargs):
            seen_queries.append(query)
            return [dict(row)]
        with patch.object(server, 'plan_topic_searches', return_value=(['batteries'], '')), patch.object(server, 'search_web', return_value=[]), patch.object(server, 'read_feed', return_value=[]), patch.object(server, 'reddit_hot_search', return_value=[]), patch.object(server, 'discover_publisher_feeds', return_value=[]), patch.object(server, 'bing_search', side_effect=news), patch.object(server, 'filter_relevant_sources', side_effect=[[], [row]]), patch.object(server, 'call_model_json', side_effect=plans) as model:
            selected, errors = server.collect_topic_sources({}, 'test', 'batteries', 5, 7)
        self.assertEqual(selected, [row])
        self.assertEqual(errors, [])
        self.assertEqual(model.call_count, 1)
        self.assertTrue(any(query.startswith('battery recycling research') for query in seen_queries))

    def test_stale_sources_excluded_before_filtering(self):
        row = {'title': 'Old battery chemistry', 'link': 'https://publisher.test/old', 'publisher': 'Publisher', 'published': '2001-01-01T00:00:00+00:00', 'excerpt': BODY, 'weight': 5}
        with patch.object(server, 'plan_topic_searches', return_value=(['batteries'], '')), patch.object(server, 'search_web', return_value=[]), patch.object(server, 'read_feed', return_value=[row]), patch.object(server, 'reddit_hot_search', return_value=[]), patch.object(server, 'discover_publisher_feeds', return_value=[]), patch.object(server, 'bing_search', return_value=[]), patch.object(server, 'filter_relevant_sources', return_value=[]) as filtering, patch.object(server, 'call_model_json', return_value={'queries': []}):
            selected, errors = server.collect_topic_sources({}, 'test', 'batteries', 5, 7)
        self.assertEqual(selected, [])
        self.assertTrue(all(not call.args[3] for call in filtering.call_args_list))

if __name__ == '__main__':
    unittest.main()
