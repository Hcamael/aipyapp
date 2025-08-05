#! /usr/bin/env python
# -*- coding: utf-8 -*-

import time
import httpx
from typing import Optional, Dict
from .base_openai import OpenAIBaseClient

class OAuth2Client(OpenAIBaseClient):
    """
    OAuth2-based OpenAI LLM client that:
    1. First gets token using client_id/client_secret
    2. Then uses the token to make LLM API calls
    """
    def __init__(self, config: Dict):
        super().__init__(config)
        self._token_url = config.get("token_url")
        self._client_id = config.get("client_id")
        self._client_secret = config.get("client_secret")
        self._access_token: Optional[str] = None
        self._token_expires = 0

    def usable(self) -> bool:
        return all([
            self._token_url,
            self._client_id,
            self._client_secret,
            self._base_url
        ])

    def _get_client(self):
        self._api_key = self._get_access_token()
        return super()._get_client()

    def _get_access_token(self) -> str:
        """Get OAuth2 access token using client credentials"""
        current_time = time.time()

        # Return existing token if it's still valid (with 300 seconds buffer)
        if self._access_token and current_time < (self._token_expires - 300):
            return self._access_token

        auth_data = {
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'grant_type': 'client_credentials'
        }

        with httpx.Client(timeout=self._timeout, verify=self._tls_verify) as client:
            response = client.post(
                self._token_url,
                data=auth_data
            )
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data['access_token']

        # Calculate expiration time (default to 5 mins if not provided)
        expires_in = token_data.get("expires_in", 300)
        self._token_expires = current_time + expires_in

        return self._access_token
        
    def get_completion(self, messages):
        response = super().get_completion(messages)
        self._client = None

        return response
