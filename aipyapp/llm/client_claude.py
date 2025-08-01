#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import Counter

from . import BaseClient, ChatMessage

# https://docs.anthropic.com/en/api/messages
class ClaudeClient(BaseClient):
    MODEL = "claude-sonnet-4-20250514"
    ENV_API_KEY = "ANTHROPIC_API_KEY"
    #PARAMS = {'thinking': {'type': 'enabled', 'budget_tokens': 1024}}

    def __init__(self, config):
        super().__init__(config)
        self._system_prompt = None

    def _get_client(self):
        import anthropic
        return anthropic.Anthropic(api_key=self._api_key, timeout=self._timeout)
    
    def usable(self):
        return super().usable() and self._api_key
    
    def _parse_usage(self, response):
        usage = response.usage
        ret = {'input_tokens': usage.input_tokens, 'output_tokens': usage.output_tokens}
        ret['total_tokens'] = ret['input_tokens'] + ret['output_tokens']
        return ret

    def _parse_stream_response(self, response, stream_processor):
        usage = Counter()    
        with stream_processor as lm:
            for event in response:
                if hasattr(event, 'delta') and hasattr(event.delta, 'text') and event.delta.text:
                    content = event.delta.text
                    lm.process_chunk(content)
                elif hasattr(event, 'message') and hasattr(event.message, 'usage') and event.message.usage:
                    usage['input_tokens'] += getattr(event.message.usage, 'input_tokens', 0)
                    usage['output_tokens'] += getattr(event.message.usage, 'output_tokens', 0)
                elif hasattr(event, 'usage') and event.usage:
                    usage['input_tokens'] += getattr(event.usage, 'input_tokens', 0)
                    usage['output_tokens'] += getattr(event.usage, 'output_tokens', 0)

        usage['total_tokens'] = usage['input_tokens'] + usage['output_tokens']
        return ChatMessage(role="assistant", content=lm.content, usage=usage)

    def _parse_response(self, response):
        content = response.content[0].text
        role = response.role
        return ChatMessage(role=role, content=content, usage=self._parse_usage(response))
    
    def add_system_prompt(self, history, system_prompt):
        self._system_prompt = system_prompt

    def get_completion(self, messages):
        if not self._client:
            self._client = self._get_client()

        message = self._client.messages.create(
            model = self._model,
            messages = messages,
            stream=self._stream,
            system=self._system_prompt,
            max_tokens = self.max_tokens,
            temperature = self._temperature,
            **self._params
        )
        return message
    