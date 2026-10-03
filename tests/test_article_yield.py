"""Quota replenishment and editorial-scope regressions; no network/model calls."""
import json
import re
import threading
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import server


def story(number):
    return {'title': f'Battery research finding {number}', 'link': f'https://publisher.test/story/{number}',
            'publisher': 'Publisher', 'published': datetime.now(timezone.utc).isoformat(),
            'excerpt': f'Researchers announced battery finding {number}.', 'feed': 'RSS', 'weight': 5}


class ArticleYieldTests(unittest.TestCase):
    def test_planner_scales_queries_and_preserves_independent_interests(self):
        queries = [f'battery research {i}' for i in range(15)]
        config = {'articleCount': 100}
        with patch.object(server, 'call_model_json', return_value={'queries': queries}) as model:
            planned, _ = server.plan_topic_searches(config, 'batteries, transit, urban gardening', 14)
        self.assertEqual(len(planned), 13)
        self.assertIn('ANY requested interest', model.call_args.args[1][0]['content'])
        self.assertIn('Do not guess counties', model.call_args.args[1][0]['content'])
        self.assertIn('target of 100 articles', model.call_args.args[1][1]['content'])

    def test_reserve_candidates_replace_rejected_slots(self):
        rows = [story(i) for i in range(6)]
        calls = []
        def consume(batch):
            calls.extend(batch)
            return batch[2:4]
        config = {'articleCount': 2, '_coverage': {'screened': 0, 'promising': 0}}
        with patch.object(server, 'call_model_json', return_value={'relevant_ids': ['1', '2', '3', '4', '5', '6']}):
            accepted = server.filter_relevant_sources(config, 'test', 'batteries', rows, 2, consume_sources=consume)
        self.assertEqual(accepted, rows[2:4])
        self.assertEqual(len(calls), 6, 'The filter must expose reserve candidates, not just two initial slots')
        self.assertEqual(config['_coverage']['screened'], 6)

    def test_full_pipeline_fills_100_after_summary_rejections(self):
        rows = [story(i) for i in range(200)]
        config = {'articleCount': 100, 'topic': 'battery research', 'searchDays': 14, 'contextLength': 131072}
        job_id = 'quota-test'
        server.JOBS[job_id] = {'id': job_id, 'status': 'running'}
        read_indices = []
        def read(item):
            number = int(item['link'].rsplit('/', 1)[-1]); read_indices.append(number)
            item.update(article_text=item['excerpt'], article_url=item['link'], read_status='Full article read', read_kind='article')
            return item
        def summary(_, batch, topic):
            accepted = []
            for index, item in batch:
                if index % 4 == 0:
                    item['_exclusion_reason'] = 'off_topic'
                    continue
                item['generated'] = {'headline': item['title'], 'section': 'Science', 'summary': item['excerpt'], 'why_it_matters': 'New findings.'}
                accepted.append((index, item))
            return accepted
        def model(config, messages, tokens):
            if config.get('_phase') == 'source relevance filter':
                candidate_rows = json.loads(re.search(r'\n(\[.*\])\nAlready selected', messages[1]['content']).group(1))
                return {'relevant_ids': [row['id'] for row in candidate_rows]}
            return {'overview': 'Battery researchers report new findings.', 'themes': []}
        try:
            with patch.object(server, 'plan_topic_searches', return_value=(['battery research'], '')), \
                 patch.object(server, 'read_feed', side_effect=lambda *args, **kwargs: [dict(row) for row in rows]), \
                 patch.object(server, 'search_web', return_value=[]), patch.object(server, 'bing_search', return_value=[]), \
                 patch.object(server, 'reddit_hot_search', return_value=[]), patch.object(server, 'discover_publisher_feeds', return_value=[]), \
                 patch.object(server, 'article_text', side_effect=read), patch.object(server, 'summarize_batch', side_effect=summary), \
                 patch.object(server, 'call_model_json', side_effect=model), patch.object(server, 'prepare_narration', return_value={'sections': []}), \
                 patch.object(server, 'close_article_browser_session'):
                server.run_job(job_id, config)
            job = server.JOBS[job_id]
            self.assertEqual(job['status'], 'done', job.get('detail'))
            result = job['result']
            self.assertEqual(len(result['articles']), 100)
            self.assertGreater(len(read_indices), 100)
            self.assertLess(len(read_indices), 150, 'Stop opening pages once the target is satisfied')
            self.assertEqual(len(read_indices), len(set(read_indices)))
            self.assertEqual(result['research_coverage']['accepted'], 100)
            self.assertEqual(result['research_coverage']['stop_reason'], 'target_reached')
            self.assertGreater(result['research_coverage']['excluded']['off_topic'], 0)
            self.assertEqual(result['research_coverage']['rounds'], 1)
        finally:
            server.JOBS.pop(job_id, None)

    def test_pipeline_workers_receive_scope_discovered_by_planner(self):
        row = story(1)
        row['title'] = 'Killeen council votes on property taxes'
        config = {'articleCount': 1, 'topic': 'Killeen taxes', 'searchDays': 14}
        job_id = 'location-test';server.JOBS[job_id] = {'id': job_id, 'status': 'running'}
        def plan(config, *args):
            config['_required_locations'] = ['Killeen']
            return ['Killeen taxes'], ''
        def read(item):
            item.update(article_text='Killeen council approved the measure.', article_url=item['link'],read_status='Full article read',read_kind='article')
        def summary(config, batch, topic):
            self.assertEqual(config.get('_required_locations'), ['Killeen'])
            for _, item in batch:
                item['generated']={'headline':item['title'],'section':'Local news','summary':item['article_text'],'why_it_matters':'Taxes changed.'}
            return batch
        try:
            with patch.object(server,'plan_topic_searches',side_effect=plan), patch.object(server,'read_feed',return_value=[row]), \
                 patch.object(server,'search_web',return_value=[]), patch.object(server,'bing_search',return_value=[]), \
                 patch.object(server,'reddit_hot_search',return_value=[]), patch.object(server,'discover_publisher_feeds',return_value=[]), \
                 patch.object(server,'article_text',side_effect=read), patch.object(server,'summarize_batch',side_effect=summary), \
                 patch.object(server,'call_model_json',return_value={'relevant_ids':['1'],'overview':'Council approves tax changes.','themes':[]}), \
                 patch.object(server,'prepare_narration',return_value={'sections':[]}), patch.object(server,'close_article_browser_session'):
                server.run_job(job_id,config)
            self.assertEqual(server.JOBS[job_id]['status'],'done',server.JOBS[job_id].get('detail'))
        finally:
            server.JOBS.pop(job_id,None)

    def test_progress_does_not_regress_during_replacement_search(self):
        server.JOBS['progress-test']={'status':'running','percent':52}
        try:
            server.update_job('progress-test',stage='Finding more stories',percent=5)
            self.assertEqual(server.JOBS['progress-test']['percent'],52)
            server.update_job('progress-test',percent=83)
            self.assertEqual(server.JOBS['progress-test']['percent'],83)
        finally:
            server.JOBS.pop('progress-test',None)

    def test_late_filter_failure_preserves_accepted_articles(self):
        rows=[story(i) for i in range(45)]
        config={'articleCount':45}
        with patch.object(server,'call_model_json',side_effect=[{'relevant_ids':['1']},server.InvalidModelJSONError('Bad JSON')]):
            accepted=server.filter_relevant_sources(config,'test','batteries',rows,45,consume_sources=lambda batch:batch)
        self.assertEqual(accepted,rows[:1])
        self.assertEqual(config['_research_stop_reason'],'verification_unavailable')
        self.assertEqual(len(config['_research_errors']),1)

    def test_cancellation_after_partial_acceptance_still_propagates(self):
        rows=[story(i) for i in range(45)]
        with patch.object(server,'call_model_json',side_effect=[{'relevant_ids':['1']},server.GenerationCancelled('Cancelled')]):
            with self.assertRaises(server.GenerationCancelled):
                server.filter_relevant_sources({},'test','batteries',rows,45,consume_sources=lambda batch:batch)

    def test_mutated_but_failed_summary_is_not_counted_as_accepted(self):
        rows=[story(i) for i in range(3)]
        config={'articleCount':3,'topic':'battery research','searchDays':14}
        job_id='partial-test';server.JOBS[job_id]={'id':job_id,'status':'running'}
        observed=[]
        def collect(config, job, topic, limit, days, consume_sources):
            config['_coverage']={'requested':3,'attempted':0,'accepted':0,'excluded':{},'screened':3,'rounds':1}
            observed.extend(consume_sources(rows[:1]))
            observed.extend(consume_sources(rows[1:]))
            config['_coverage'].update(accepted=len(observed),stop_reason=config.get('_research_stop_reason','target_reached'))
            return observed,[]
        def read(item):
            item.update(article_text=item['excerpt'],article_url=item['link'],read_status='Full article read',read_kind='article')
        def summary(config,batch,topic):
            for index,item in batch:
                item['generated']={'headline':item['title'],'section':'Science','summary':item['excerpt'],'why_it_matters':'New findings.'}
            if any(index>0 for index,_ in batch):
                raise RuntimeError('A retry failed after setting a valid generated row')
            return batch
        try:
            with patch.object(server,'collect_topic_sources',side_effect=collect), patch.object(server,'article_text',side_effect=read), \
                 patch.object(server,'summarize_batch',side_effect=summary), patch.object(server,'call_model_json',side_effect=RuntimeError('Model disconnected')), \
                 patch.object(server,'prepare_narration',return_value={'sections':[]}),patch.object(server,'close_article_browser_session'):
                server.run_job(job_id,config)
            job=server.JOBS[job_id];self.assertEqual(job['status'],'done',job.get('detail'))
            self.assertEqual(len(job['result']['articles']),1)
            self.assertEqual(job['result']['research_coverage']['accepted'],1)
            self.assertEqual(job['result']['research_coverage']['stop_reason'],'verification_unavailable')
            self.assertEqual(len(observed),1)
            self.assertTrue(all('generated' not in item for item in rows[1:]))
        finally:
            server.JOBS.pop(job_id,None)

    def test_search_rounds_are_bounded_when_topic_has_few_stories(self):
        count = 0
        def feed(*args, **kwargs):
            nonlocal count
            count += 1
            return [story(count)]
        def model(*args, **kwargs):
            return {'queries': [f'new research angle {count}']}
        config = {'articleCount': 100}
        with patch.object(server, 'plan_topic_searches', return_value=(['batteries'], '')), \
             patch.object(server, 'read_feed', side_effect=feed), patch.object(server, 'search_web', return_value=[]), \
             patch.object(server, 'bing_search', return_value=[]), patch.object(server, 'reddit_hot_search', return_value=[]), \
             patch.object(server, 'discover_publisher_feeds', return_value=[]), patch.object(server, 'call_model_json', side_effect=model), \
             patch.object(server, 'filter_relevant_sources', return_value=[]):
            selected, _ = server.collect_topic_sources(config, 'test', 'batteries', 100, 14)
        self.assertEqual(selected, [])
        self.assertEqual(config['_coverage']['rounds'], 4)
        self.assertEqual(config['_coverage']['stop_reason'], 'search_round_limit')

    def test_small_paper_does_not_stop_at_160_candidates(self):
        rows=[story(i) for i in range(201)]
        published=datetime.now(timezone.utc).isoformat()
        for row in rows:
            row['published']=published
        def model(config,messages,tokens):
            candidates=json.loads(re.search(r'\n(\[.*\])\nAlready selected',messages[1]['content']).group(1))
            return {'relevant_ids':[row['id'] for row in candidates if row['headline'].endswith('199')]}
        config={'articleCount':1}
        with patch.object(server,'plan_topic_searches',return_value=(['batteries'],'')),patch.object(server,'read_feed',return_value=rows), \
             patch.object(server,'search_web',return_value=[]),patch.object(server,'bing_search',return_value=[]), \
             patch.object(server,'reddit_hot_search',return_value=[]),patch.object(server,'discover_publisher_feeds',return_value=[]), \
             patch.object(server,'call_model_json',side_effect=model):
            selected,_=server.collect_topic_sources(config,'test','batteries',1,14)
        self.assertEqual(len(selected),1)
        self.assertTrue(selected[0]['title'].endswith('199'))
        self.assertGreater(config['_coverage']['screened'],160)
        self.assertEqual(config['_coverage']['stop_reason'],'target_reached')

    def test_empty_followup_plan_does_not_count_as_a_search_round(self):
        config={'articleCount':8}
        with patch.object(server,'plan_topic_searches',return_value=(['batteries'],'')),patch.object(server,'read_feed',return_value=[]), \
             patch.object(server,'search_web',return_value=[]),patch.object(server,'bing_search',return_value=[]), \
             patch.object(server,'reddit_hot_search',return_value=[]),patch.object(server,'discover_publisher_feeds',return_value=[]), \
             patch.object(server,'call_model_json',return_value={'queries':[]}):
            server.collect_topic_sources(config,'test','batteries',8,14)
        self.assertEqual(config['_coverage']['rounds'],1)
        self.assertEqual(config['_coverage']['stop_reason'],'no_new_queries')

    def test_cancelled_search_never_starts_network_work(self):
        event = threading.Event();event.set()
        with patch.object(server, 'search_web') as search:
            with self.assertRaises(server.GenerationCancelled):
                server.collect_topic_sources({'_cancel_event': event}, 'test', 'batteries')
        search.assert_not_called()

    def test_quote_presentation_differences_do_not_discard_article(self):
        row = story(1);row.update(article_url=row['link'],read_status='Full article read',article_text='Scientists’ batteries — tested in labs — last longer.')
        answer = {'summaries': [{'id':'0','relevant':True,'relevance_evidence':"Scientists' batteries - tested in labs - last longer.",'headline':'Batteries last longer','summary':'Scientists report longer-lasting batteries.'}]}
        with patch.object(server,'call_model_json',return_value=answer):
            self.assertEqual(len(server.summarize_batch({},[(0,row)],'batteries')),1)

    def test_missing_summary_retries_without_publishing_unchecked_article(self):
        row = story(1);row.update(article_url=row['link'],read_status='Full article read',article_text=row['excerpt'])
        answer = {'summaries': [{'id':'0','relevant':True,'relevance_evidence':row['excerpt'],'headline':row['title'],'summary':'Scientists report findings.'}]}
        with patch.object(server,'call_model_json',side_effect=[{'summaries':[]},answer]) as model:
            self.assertEqual(len(server.summarize_batch({},[(0,row)],'batteries')),1)
        self.assertEqual(model.call_count,2)

    def test_title_is_source_evidence_but_publisher_is_not(self):
        row = story(1);row.update(title='Killeen council votes on taxes',publisher='Killeen newspaper',article_url=row['link'],read_status='Feed excerpt only',article_text='Members approved the proposal.')
        answer = {'summaries':[{'id':'0','relevant':True,'relevance_evidence':row['title'],'headline':row['title'],'summary':'The council approved the proposal.'}]}
        with patch.object(server,'call_model_json',return_value=answer):
            self.assertEqual(len(server.summarize_batch({'_required_locations':['Killeen']},[(0,row)],'Killeen taxes')),1)
        answer['summaries'][0]['relevance_evidence']='Killeen newspaper'
        with patch.object(server,'call_model_json',return_value=answer):
            self.assertEqual(server.summarize_batch({'_required_locations':['Killeen']},[(0,row)],'Killeen taxes'),[])

if __name__ == '__main__':
    unittest.main()
