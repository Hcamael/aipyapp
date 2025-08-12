#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from aipyapp import TaskPlugin

class WebToolsPlugin(TaskPlugin):
    """网络工具插件 - 提供网页抓取、URL分析等功能"""
    
    name = "web_tools"
    version = "1.0.0"
    description = "提供网页抓取、URL分析、HTTP请求等网络工具功能"
    author = "AiPy Team"
    
    def init(self):
        """初始化网络工具配置"""
        self.timeout = self.config.get('timeout', 30)
        self.user_agent = self.config.get('user_agent', 'AiPy WebTools/1.0')
        self.max_content_length = self.config.get('max_content_length', 1024 * 1024)  # 1MB
        self.headers = {
            'User-Agent': self.user_agent,
            **self.config.get('default_headers', {})
        }
        
        self.logger.info(f"初始化网络工具，超时: {self.timeout}s")
    
    def fn_fetch_webpage(self, url: str, extract_text: bool = True) -> Dict[str, Any]:
        """
        抓取网页内容
        
        Args:
            url: 目标URL
            extract_text: 是否只提取文本内容
            
        Returns:
            包含网页信息的字典
        
        Examples:
            >>> fn_fetch_webpage("https://www.baidu.com")
            {'success': True, 'url': 'https://www.baidu.com', 'status_code': 200, 'headers': {'Content-Type': 'text/html; charset=utf-8'}, 'content_type': 'text/html; charset=utf-8', 'encoding': 'utf-8', 'text': '百度一下，你就知道', 'title': '百度一下，你就知道'}
            >>> fn_fetch_webpage("https://www.baidu.com", extract_text=False)
            {'success': True, 'url': 'https://www.baidu.com', 'status_code': 200, 'headers': {'Content-Type': 'text/html; charset=utf-8'}, 'content_type': 'text/html; charset=utf-8', 'encoding': 'utf-8', 'content': '<!DOCTYPE html>...'}    
        """
        return self._fetch_webpage(url, extract_text)
    
    def fn_http_request(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            url: 请求URL
            method: HTTP方法 (GET/POST/PUT/DELETE等)
            headers: 请求头
            params: URL参数
            json_data: JSON请求体
                
        Returns:
            包含网页信息的字典，其中content为响应内容，success为是否成功，status_code为状态码

        Examples:
            >>> fn_http_request("https://www.baidu.com")
            {'success': True, 'status_code': 200, 'headers': {'Content-Type': 'text/html; charset=utf-8'}, 'content': '百度一下，你就知道', 'elapsed': '0.000000s'}
            >>> fn_http_request("https://www.baidu.com", method="POST", json_data={"name": "John", "age": 30})
            {'success': True, 'status_code': 200, 'headers': {'Content-Type': 'text/html; charset=utf-8'}, 'content': '百度一下，你就知道', 'elapsed': '0.000000s'}
            >>> fn_http_request("https://www.baidu.com")
            {'sucess': False, 'error': '400 Client Error: Bad Request for url'}
        """
        return self._http_request(url, method, headers, params, json_data)
        
    def fn_analyze_url(self, url: str) -> Dict[str, str]:
        """
        分析URL的各个组成部分
        
        Args:
            url: 待分析的URL
            
        Returns:
            URL组成信息字典
        """
        return self._analyze_url(url)
    
    def fn_check_url_status(self, url: str) -> Dict[str, Any]:
        """
        检查URL状态
        
        Args:
            url: 目标URL
            
        Returns:
            URL状态信息字典
        """
        return self._check_url_status(url)
    
    def _fetch_webpage(self, url: str, extract_text: bool) -> Dict[str, Any]:
        """抓取网页内容"""
        try:
            response = requests.get(
                url, 
                headers=self.headers,
                timeout=self.timeout,
                stream=True
            )
            
            # 检查内容长度
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.max_content_length:
                return {
                    "success": False,
                    "error": f"内容太大 ({content_length} bytes)，超过限制 ({self.max_content_length} bytes)"
                }
            
            response.raise_for_status()
            
            result = {
                "success": True,
                "url": url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": response.headers.get('content-type', ''),
                "encoding": response.encoding
            }
            
            if extract_text and 'text/html' in response.headers.get('content-type', ''):
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # 移除script和style标签
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    result["text"] = soup.get_text(separator=' ', strip=True)
                    result["title"] = soup.title.string if soup.title else ""
                    
                except ImportError:
                    result["text"] = response.text
                    result["raw_html"] = response.text[:2000] + "..." if len(response.text) > 2000 else response.text
            else:
                result["content"] = response.text[:2000] + "..." if len(response.text) > 2000 else response.text
            
            return result
            
        except Exception as e:
            self.logger.error(f"抓取网页失败 {url}: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }
    
    def _analyze_url(self, url: str) -> Dict[str, str]:
        """分析URL结构"""
        try:
            parsed = urlparse(url)
            return {
                "scheme": parsed.scheme,
                "netloc": parsed.netloc,
                "hostname": parsed.hostname,
                "port": str(parsed.port) if parsed.port else "",
                "path": parsed.path,
                "params": parsed.params,
                "query": parsed.query,
                "fragment": parsed.fragment,
                "username": parsed.username or "",
                "password": "***" if parsed.password else ""
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _http_request(self, url: str, method: str, headers: Optional[Dict], params: Optional[Dict], json_data: Optional[Dict]) -> Dict[str, Any]:
        """发送HTTP请求"""
        try:
            request_headers = self.headers.copy()
            if headers:
                request_headers.update(headers)
            
            kwargs = {
                'headers': request_headers,
                'timeout': self.timeout,
                'params': params
            }
            
            if json_data:
                kwargs['json'] = json_data
            
            response = requests.request(method.upper(), url, **kwargs)
            
            return {
                "success": True,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.text,
                "elapsed": str(response.elapsed)
            }
            
        except Exception as e:
            self.logger.error(f"HTTP请求失败 {method} {url}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _check_url_status(self, url: str) -> Dict[str, Any]:
        """检查URL状态"""
        try:
            response = requests.head(url, headers=self.headers, timeout=self.timeout)
            return {
                "accessible": True,
                "status_code": response.status_code,
                "content_type": response.headers.get('content-type', ''),
                "content_length": response.headers.get('content-length', ''),
                "last_modified": response.headers.get('last-modified', ''),
                "server": response.headers.get('server', '')
            }
        except Exception as e:
            return {
                "accessible": False,
                "error": str(e)
            }