"""Protocol regressions for the OpenAI-compatible streaming reader."""
import io
import json
import unittest

from chat_stream import completion_events


class Response(io.BytesIO):
    def __init__(self, body, content_type='text/event-stream'):
        super().__init__(body.encode('utf-8'))
        self.headers = {'Content-Type': content_type}


def frame(delta=None, finish=None, index=0):
    choice = {'index': index, 'delta': delta or {}, 'finish_reason': finish}
    return 'data: ' + json.dumps({'choices': [choice]}, ensure_ascii=False) + '\n\n'


class ChatStreamTests(unittest.TestCase):
    def test_content_unicode_and_completion(self):
        response = Response(': keepalive\n\n' + frame({'role': 'assistant'}) + frame({'content': 'Hello 🌿 café'}) + frame(finish='stop') + 'data: [DONE]\n\n')
        self.assertEqual(list(completion_events(response)), [{'delta': 'Hello 🌿 café'}, {'finish_reason': 'stop'}])

    def test_reasoning_and_other_choices_remain_private(self):
        response = Response(frame({'reasoning_content': 'Private analysis'}) + frame({'content': 'Other choice'}, index=1) + frame({'content': [{'type': 'text', 'text': 'Visible'}]}) + frame(finish='length'))
        self.assertEqual(list(completion_events(response)), [{'delta': 'Visible'}, {'finish_reason': 'length'}])

    def test_json_provider_compatibility(self):
        payload = {'choices': [{'message': {'content': 'Complete answer'}, 'finish_reason': 'stop'}]}
        self.assertEqual(list(completion_events(Response(json.dumps(payload), 'application/json'))), [{'delta': 'Complete answer'}, {'finish_reason': 'stop'}])

    def test_done_marker_without_finish_chunk(self):
        self.assertEqual(list(completion_events(Response(frame({'content': 'Answer'}) + 'data: [DONE]\n\n'))), [{'delta': 'Answer'}])

    def test_interrupted_stream_keeps_partial_then_raises(self):
        stream = completion_events(Response(frame({'content': 'Partial answer'})))
        self.assertEqual(next(stream), {'delta': 'Partial answer'})
        with self.assertRaisesRegex(RuntimeError, 'ended before completing'):
            next(stream)

    def test_error_frame(self):
        with self.assertRaisesRegex(RuntimeError, 'error while streaming'):
            list(completion_events(Response('data: {"error":{"message":"Failed"}}\n\n')))

    def test_cancelled_reader_stops_before_content(self):
        self.assertEqual(list(completion_events(Response(frame({'content': 'Must not appear'})), lambda: True)), [])


class ResearchDecisionTests(unittest.TestCase):
    def test_decision_uses_configured_model_and_existing_context(self):
        from unittest.mock import patch
        import server
        config = {'model': 'configured-model'}
        messages = [{'role': 'user', 'content': 'Explain this supplied text'}]
        with patch.object(server, 'call_model_json', return_value={'search': False, 'query': ''}) as model:
            self.assertEqual(server.plan_chat_research(config, messages, 'Explain this'), (False, ''))
        self.assertEqual(model.call_args.args[0]['model'], 'configured-model')
        self.assertIn('Explain this supplied text', model.call_args.args[1][1]['content'])

    def test_search_requires_explicit_boolean_and_bounds_query(self):
        from unittest.mock import patch
        import server
        for decision, expected in [({'search': True, 'query': 'x' * 400}, (True, 'x' * 240)), ({'search': 'true', 'query': ''}, (False, ''))]:
            with patch.object(server, 'call_model_json', return_value=decision):
                self.assertEqual(server.plan_chat_research({}, [{'role': 'user', 'content': 'Current events?'}], 'Current events?'), expected)

if __name__ == '__main__':
    unittest.main()
