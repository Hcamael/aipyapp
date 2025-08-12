#!/usr/bin/env python
# -*- coding: utf-8 -*-

from base64 import b64encode
import re
from pathlib import Path
from typing import Union, List, Dict, Any
import mimetypes

from loguru import logger
from charset_normalizer import from_bytes

MessageList = List[Dict[str, Any]]
LLMContext = Union[str, MessageList]

class MMContentError(Exception):
    """多模态内容处理的基础异常类"""
    pass

class FileReadError(MMContentError):
    """文件读取失败异常"""
    def __init__(self, file_path: str, original_error: Exception):
        self.file_path = file_path
        self.original_error = original_error
        super().__init__(f"无法读取文件 {file_path}: {original_error}")

def is_text_file(path, blocksize=4096):
    try:
        with open(path, 'rb') as f:
            chunk = f.read(blocksize)
        result = from_bytes(chunk)
        if not result:
            return False
        best = result.best()
        if best is None:
            return False
        # encoding 存在且 chaos 很低，认为是文本
        if best.encoding and best.chaos < 0.1:
            return True
        return False
    except Exception:
        logger.exception('Failed to check if file is text')
        return False

class MMContent:
    """
    多模态内容类，支持文本、图片、文件的统一处理。
    """
    def __init__(self, string: str, base_path: Path = None):
        self.string = string
        self.items = self._from_string(string, base_path)
        self.log = logger.bind(type='multimodal')

    def _from_string(self, text: str, base_path: Path = None) -> list:
        """
        从输入字符串解析多模态内容，支持@file.pdf、@image.jpg等文件引用，返回MMContent对象
        支持带引号的文件路径，如 @"path with spaces.txt"
        """
        # 匹配 @文件路径，支持带引号的路径
        parts = re.split(r'(@(?:"[^"]*"|\'[^\']*\'|[^\s]+))', text)
        items = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if part.startswith('@'):
                file_path = part[1:]
                # 去除文件路径的引号
                if (file_path.startswith('"') and file_path.endswith('"')) or \
                   (file_path.startswith("'") and file_path.endswith("'")):
                    file_path = file_path[1:-1]
                ext = Path(file_path).suffix.lower()
                file_type = 'image' if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'} else None
                if base_path:
                    p = Path(file_path)
                    if not p.is_absolute():
                        file_path = str(base_path / p)
                
                # 检查文件是否存在，如果不存在则作为普通文本处理
                if not Path(file_path).exists():
                    items.append({'type': 'text', 'text': part})
                    continue
                
                if not file_type:
                    # 判断文本/二进制
                    if is_text_file(file_path):
                        file_type = 'document'
                    else:
                        file_type = 'file'
                items.append({'type': file_type, 'path': file_path})
            else:
                items.append({'type': 'text', 'text': part})
        return items

    @property
    def is_multimodal(self) -> bool:
        return any(item['type'] in ('image', 'file', 'document') for item in self.items)
    
    def _is_network_url(self, url: str) -> bool:
        """判断是否为网络URL"""
        return url.startswith(('http://', 'https://', 'data:'))
    
    def _get_mime_type(self, file_path: str, default_mime: str) -> str:
        """获取文件的MIME类型"""
        mime, _ = mimetypes.guess_type(file_path)
        return mime or default_mime
    
    def _read_file(self, file_path: str, base64: bool = False) -> str:
        """读取文件内容，支持 base64 编码"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            if base64:
                data = b64encode(data)
            return data.decode('utf-8')
        except Exception as e:
            raise FileReadError(file_path, e)

    def _process_image_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """处理图片项"""
        url = item['path']
        
        # 网络URL直接使用
        if self._is_network_url(url):
            return {"type": "image_url", "image_url": {"url": url}}
        
        # 本地图片转换为data URL
        mime = self._get_mime_type(url, 'image/jpeg')
        b64_data = self._read_file(url, base64=True)
        data_url = f"data:{mime};base64,{b64_data}"
        return {"type": "image_url", "image_url": {"url": data_url}}
    
    def _process_file_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """处理文件项（仅二进制文件）"""
        return {"type": "text", "text": f"file: {item['path']}"}

    def _process_document_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """处理文本文件项（document）"""
        path = str(item['path'])
        content = self._read_file(path, base64=False)
        text = f"<attachment filename=\"{path}\">{content}</attachment>"
        return {"type": "text", "text": text}

    def _process_text_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """处理文本项"""
        return {"type": "text", "text": item['text']}
    
    @property
    def content(self) -> LLMContext:
        """返回多模态内容的结构化列表

        转换为 LLM API 可接受的 context 格式：
        - 只有一个纯文本时，直接返回字符串
        - 图片：image_url，自动转data url
        - 文本文件（document）：转为text类型，内容包裹在<document>标签
        - 文件（如PDF等二进制）：file类型
        - 文本文件（document）：转为text类型，内容包裹在<document>标签
        - 文件（如PDF等二进制）：file类型
        """
        results = []
        has_image = False
        for item in self.items:
            if item['type'] == 'text':
                result = self._process_text_item(item)
            elif item['type'] == 'image':
                has_image = True
                result = self._process_image_item(item)
            elif item['type'] == 'document':
                result = self._process_document_item(item)
            else:
                # TODO: 处理其他类型
                result = self._process_file_item(item)
            results.append(result)

        if not has_image:
            texts = [r['text'] for r in results if r['type'] == 'text']
            return '\n'.join(texts)
        return results
    