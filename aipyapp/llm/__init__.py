#! /usr/bin/env python
# -*- coding: utf-8 -*-


from .. import T
from .base import ChatMessage, BaseClient
from .base_openai import OpenAIBaseClient
from .client_claude import ClaudeClient
from .client_ollama import OllamaClient
from .client_oauth2 import OAuth2Client
from .models import ModelRegistry, ModelCapability

__all__ = ['ChatMessage', 'CLIENTS', 'ModelRegistry', 'ModelCapability']

class OpenAIClient(OpenAIBaseClient): 
    MODEL = 'gpt-4o'

class GeminiClient(OpenAIBaseClient): 
    BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/'
    MODEL = 'gemini-2.5-flash'

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

class MoonShotClient(OpenAIBaseClient): 
    BASE_URL = T('https://api.moonshot.ai/v1')
    MODEL = 'kimi-latest'

class BigModelClient(OpenAIBaseClient): 
    BASE_URL = 'https://open.bigmodel.cn/api/paas/v4'
    MODEL = 'glm-4.5-air'

class ZClient(OpenAIBaseClient):
    BASE_URL = 'https://api.z.ai/api/paas/v4'
    MODEL = 'glm-4.5-flash'

CLIENTS = {
    "openai": OpenAIClient,
    "ollama": OllamaClient,
    "claude": ClaudeClient,
    "gemini": GeminiClient,
    "deepseek": DeepSeekClient,
    'grok': GrokClient,
    'trust': TrustClient,
    'azure': AzureOpenAIClient,
    'oauth2': OAuth2Client,
    'doubao': DoubaoClient,
    'kimi': MoonShotClient,
    'bigmodel': BigModelClient,
    'z': ZClient
}

