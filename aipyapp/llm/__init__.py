#! /usr/bin/env python
# -*- coding: utf-8 -*-


from .. import T
from .base import ChatMessage, BaseClient
from .base_openai import OpenAIBaseClient
from .client_claude import ClaudeClient
from .client_ollama import OllamaClient

__all__ = ['ChatMessage', 'CLIENTS']

class OpenAIClient(OpenAIBaseClient): 
    MODEL = 'gpt-4o'

class GeminiClient(OpenAIBaseClient): 
    BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/'
    MODEL = 'gemini-2.5-flash-preview-05-20'

class DeepSeekClient(OpenAIBaseClient): 
    BASE_URL = 'https://api.deepseek.com'
    MODEL = 'deepseek-chat'

class GrokClient(OpenAIBaseClient): 
    BASE_URL = 'https://api.x.ai/v1/'
    MODEL = 'grok-3-mini'

class TrustClient(OpenAIBaseClient): 
    MODEL = 'auto'

    def get_base_url(self):
        return self.config.get("base_url") or T("https://sapi.trustoken.ai/v1")
    
class AzureOpenAIClient(OpenAIBaseClient): 
    MODEL = 'gpt-4o'

    def __init__(self, config):
        super().__init__(config)
        self._end_point = config.get('endpoint')

    def usable(self):
        return super().usable() and self._end_point
    
    def _get_client(self):
        from openai import AzureOpenAI
        return AzureOpenAI(azure_endpoint=self._end_point, api_key=self._api_key, api_version="2024-02-01")

class DoubaoClient(OpenAIBaseClient): 
    BASE_URL = 'https://ark.cn-beijing.volces.com/api/v3'
    MODEL = 'doubao-seed-1.6-250615'

CLIENTS = {
    "openai": OpenAIClient,
    "ollama": OllamaClient,
    "claude": ClaudeClient,
    "gemini": GeminiClient,
    "deepseek": DeepSeekClient,
    'grok': GrokClient,
    'trust': TrustClient,
    'azure': AzureOpenAIClient,
    'doubao': DoubaoClient
}

