"""Tests for token interceptor proxy and token parsing mechanics."""

from scripts.proxy import TokenAccumulator, parse_token_payload


def test_parse_openai_standard_json():
    accumulator = TokenAccumulator()
    raw_json = '{"id": "chatcmpl-123", "usage": {"prompt_tokens": 150, "completion_tokens": 75, "total_tokens": 225}}'

    parse_token_payload(raw_json, accumulator)
    usage = accumulator.get_usage()

    assert usage.input_tokens == 150
    assert usage.output_tokens == 75
    assert usage.total_tokens == 225


def test_parse_openai_sse_stream():
    accumulator = TokenAccumulator()
    sse_chunks = (
        'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n'
        'data: {"choices": [{"delta": {"content": " World"}}]}\n\n'
        'data: {"choices": [], "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}}\n\n'
        'data: [DONE]\n\n'
    )

    parse_token_payload(sse_chunks, accumulator)
    usage = accumulator.get_usage()

    assert usage.input_tokens == 20
    assert usage.output_tokens == 10
    assert usage.total_tokens == 30


def test_parse_anthropic_sse_stream():
    accumulator = TokenAccumulator()
    anthropic_stream = (
        'event: message_start\n'
        'data: {"type": "message_start", "message": {"id": "msg_123", "usage": {"input_tokens": 80}}}\n\n'
        'event: content_block_delta\n'
        'data: {"type": "content_block_delta", "delta": {"text": "Code"}}\n\n'
        'event: message_delta\n'
        'data: {"type": "message_delta", "usage": {"output_tokens": 45}}\n\n'
    )

    parse_token_payload(anthropic_stream, accumulator)
    usage = accumulator.get_usage()

    assert usage.input_tokens == 80
    assert usage.output_tokens == 45
    assert usage.total_tokens == 125
