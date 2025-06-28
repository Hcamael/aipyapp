#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import Counter

import httpx
import openai
from loguru import logger

from .. import T
from . import BaseClient, ChatMessage

# https://platform.openai.com/docs/api-reference/chat/create
# https://api-docs.deepseek.com/api/create-chat-completion
class OpenAIBaseClient(BaseClient):
    PARAMS = {'stream_options': {'include_usage': True}}
    
    def usable(self):
        return super().usable() and self._api_key
    
    def _get_client(self):
        return openai.Client(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=self._timeout,
            http_client=httpx.Client(
                verify=self._tls_verify
            )
        )
    
    def add_system_prompt(self, history, system_prompt):
        history.add("system", system_prompt)

    def _parse_usage(self, usage):
        try:
            reasoning_tokens = int(usage.completion_tokens_details.reasoning_tokens)
        except Exception:
            reasoning_tokens = 0

        usage = Counter({'total_tokens': usage.total_tokens,
                'input_tokens': usage.prompt_tokens,
                'output_tokens': usage.completion_tokens + reasoning_tokens})
        return usage
    
    def _parse_stream_response(self, response, stream_processor):
        usage = Counter()
        with stream_processor as lm:
            for chunk in response:
                #print(chunk)
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    usage = self._parse_usage(chunk.usage)

                if chunk.choices:
                    content = None
                    delta = chunk.choices[0].delta
                    if delta.content:
                        reason = False
                        content = delta.content
                    elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        reason = True
                        content = delta.reasoning_content
                    if content:
                        lm.process_chunk(content, reason=reason)

        return ChatMessage(role="assistant", content=lm.content, reason=lm.reason, usage=usage)

    def _parse_response(self, response):
        message = response.choices[0].message
        reason = getattr(message, "reasoning_content", None)
        return ChatMessage(
            role=message.role,
            content=message.content,
            reason=reason,
            usage=self._parse_usage(response.usage)
        )

    def get_completion(self, messages):
        if not self._client:
            self._client = self._get_client()

        response = self._client.chat.completions.create(
            model = self._model,
            messages = messages,
            stream=self._stream,
            max_tokens = self.max_tokens,
            **self._params
        )
        return response
    