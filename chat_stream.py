"""Read OpenAI-compatible Chat Completions streams without an SDK."""
import json


def content_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ''.join(part.get('text', '') for part in value if isinstance(part, dict) and isinstance(part.get('text'), str))
    return ''


def completion_events(response, should_stop=lambda: False):
    """Yield content/finish events; reasoning and other choices remain private."""
    if 'application/json' in response.headers.get('Content-Type', ''):
        payload = json.loads(response.read(8_000_000))
        if payload.get('error'):
            raise RuntimeError('The model endpoint returned an error response.')
        choice = (payload.get('choices') or [{}])[0]
        text = content_text((choice.get('message') or {}).get('content'))
        if text:
            yield {'delta': text}
        yield {'finish_reason': choice.get('finish_reason')}
        return

    data_lines = []
    finished = False
    for raw in response:
        if should_stop():
            return
        if len(raw) > 1_000_000:
            raise RuntimeError("The model endpoint returned an oversized stream event.")
        line = raw.decode('utf-8').rstrip('\r\n')
        if line.startswith('data:'):
            data_lines.append(line[5:].lstrip(' '))
        elif not line and data_lines:
            data = '\n'.join(data_lines)
            data_lines.clear()
            if data.strip() == '[DONE]':
                finished = True
                break
            payload = json.loads(data)
            if payload.get('error'):
                raise RuntimeError('The model endpoint returned an error while streaming.')
            for choice in payload.get('choices') or []:
                if choice.get('index', 0) != 0:
                    continue
                text = content_text((choice.get('delta') or {}).get('content'))
                if text:
                    yield {'delta': text}
                if choice.get('finish_reason'):
                    finished = True
                    yield {'finish_reason': choice['finish_reason']}
                    return
    if not finished:
        raise RuntimeError('The model stream ended before completing its response.')
