#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests

from . import BaseClient, ChatMessage

# https://github.com/ollama/ollama/blob/main/docs/api.md
class OllamaClient(BaseClient):
    def __init__(self, config):
        super().__init__(config)
        self._session = requests.Session()

    def usable(self):
        return super().usable() and self._base_url
    
    def _parse_usage(self, response):
        ret = {'input_tokens': response['prompt_eval_count'], 'output_tokens': response['eval_count']}
        ret['total_tokens'] = ret['input_tokens'] + ret['output_tokens']
        return ret

    def _parse_stream_response(self, response, stream_processor):
        with stream_processor as lm:
            for chunk in response.iter_lines():
                chunk = chunk.decode(encoding='utf-8')
                msg = json.loads(chunk)
                if msg['done']:
                    usage = self._parse_usage(msg)
                    break

                if 'message' in msg and 'content' in msg['message'] and msg['message']['content']:
                    content = msg['message']['content']
                    lm.process_chunk(content)

        return ChatMessage(role="assistant", content=lm.content, usage=usage)

    def _parse_response(self, response):
        response = response.json()
        msg = response["message"]
        return ChatMessage(role=msg['role'], content=msg['content'], usage=self._parse_usage(response))
    
    def get_completion(self, messages):
        response = self._session.post(
            f"{self._base_url}/api/chat",
            json={
                "model": self._model,
                "messages": messages,
                "stream": self._stream,
                "options": {"num_predict": self.max_tokens, "temperature": self._temperature}
            },
            timeout=self._timeout,
            **self._params
        )
        response.raise_for_status()
        return response
