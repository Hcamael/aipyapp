#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import Counter, defaultdict, namedtuple
from typing import Union, List, Dict, Any

from loguru import logger

from .. import T, __respath__
from ..llm import CLIENTS, ChatMessage, ModelRegistry, ModelCapability
from .multimodal import LLMContext

class LineReceiver(list):
    def __init__(self):
        super().__init__()
        self.buffer = ""

    @property
    def content(self):
        return '\n'.join(self)
    
    def feed(self, data: str):
        self.buffer += data
        new_lines = []

        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            if line:
                self.append(line)
                new_lines.append(line)

        return new_lines
    
    def empty(self):
        return not self and not self.buffer
    
    def done(self):
        buffer = self.buffer
        if buffer:
            self.append(buffer)
            self.buffer = ""
        return buffer

class StreamProcessor:
    """流式数据处理器，负责处理 LLM 流式响应并发送事件"""
    
    def __init__(self, task, name):
        self.task = task
        self.name = name
        self.lr = LineReceiver()
        self.lr_reason = LineReceiver()

    @property
    def content(self):
        return self.lr.content
    
    @property
    def reason(self):
        return self.lr_reason.content
    
    def __enter__(self):
        """支持上下文管理器协议"""
        self.task.broadcast('stream_start', {'llm': self.name})
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器协议"""
        if self.lr.buffer:
            self.process_chunk('\n')        
        self.task.broadcast('stream_end', {'llm': self.name})
    
    def process_chunk(self, content, *, reason=False):
        """处理流式数据块并发送事件"""
        if not content: 
            return

        # 处理思考内容的结束
        if not reason and self.lr.empty() and not self.lr_reason.empty():
            line = self.lr_reason.done()
            if line:
                self.task.broadcast('stream', {
                    'llm': self.name, 
                    'lines': [line, "\n\n----\n\n"], 
                    'reason': True
                })

        # 处理当前数据块
        lr = self.lr_reason if reason else self.lr
        lines = lr.feed(content)
        if not lines:
            return
        
        # 过滤掉特殊注释行
        lines2 = [line for line in lines if not line.startswith('<!-- Block-') and not line.startswith('<!-- Cmd-')]
        if lines2:
            self.task.broadcast('stream', {
                'llm': self.name, 
                'lines': lines2, 
                'reason': reason
            })

class ChatHistory:
    def __init__(self):
        self.messages = []
        self._total_tokens = Counter()

    def __len__(self):
        return len(self.messages)
    
    def json(self):
        return [msg.__dict__ for msg in self.messages]
    
    def add(self, role, content):
        self.add_message(ChatMessage(role=role, content=content))

    def add_message(self, message: ChatMessage):
        self.messages.append(message)
        self._total_tokens += message.usage

    def get_usage(self):
        return iter(row.usage for row in self.messages if row.role == "assistant")
    
    def get_summary(self):
        summary = {'time': 0, 'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
        summary.update(dict(self._total_tokens))
        summary['rounds'] = sum(1 for row in self.messages if row.role == "assistant")
        return summary

    def get_messages(self):
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]



class ClientManager(object):
    MAX_TOKENS = 8192

    def __init__(self, settings):
        self.clients = {}
        self.default = None
        self.current = None
        self.log = logger.bind(src='client_manager')
        self.names = self._init_clients(settings)
        self.model_registry = ModelRegistry(__respath__ / "models.yaml")

    def _create_client(self, config):
        kind = config.get("type", "openai")
        client_class = CLIENTS.get(kind.lower())
        if not client_class:
            self.log.error('Unsupported LLM provider', kind=kind)
            return None
        return client_class(config)
    
    def _init_clients(self, settings):
        names = defaultdict(set)
        max_tokens = settings.get('max_tokens', self.MAX_TOKENS)
        for name, config in settings.llm.items():
            if not config.get('enable', True):
                names['disabled'].add(name)
                continue
            
            config['name'] = name
            try:
                client = self._create_client(config)
            except Exception as e:
                self.log.exception('Error creating LLM client', config=config)
                names['error'].add(name)
                continue

            if not client or not client.usable():
                names['disabled'].add(name)
                self.log.error('LLM client not usable', name=name, config=config)
                continue

            names['enabled'].add(name)
            if not client.max_tokens:
                client.max_tokens = max_tokens
            self.clients[name] = client

            if config.get('default', False) and not self.default:
                self.default = client
                names['default'] = name

        if not self.default:
            name = list(self.clients.keys())[0]
            self.default = self.clients[name]
            names['default'] = name

        self.current = self.default
        return names

    def __len__(self):
        return len(self.clients)
    
    def __repr__(self):
        return f"Current: {'default' if self.current == self.default else self.current}, Default: {self.default}"
    
    def __contains__(self, name):
        return name in self.clients
    
    def use(self, name):
        client = self.clients.get(name)
        if client and client.usable():
            self.current = client
            return True
        return False

    def get_client(self, name):
        return self.clients.get(name)
    
    def Client(self, task):
        return Client(self, task)
    
    def to_records(self):
        LLMRecord = namedtuple('LLMRecord', ['Name', 'Model', 'Max_Tokens', 'Base_URL'])
        rows = []
        for name, client in self.clients.items():
            rows.append(LLMRecord(name, client.model, client.max_tokens, client.base_url))
        return rows
    
    def get_model_info(self, model: str):
        return self.model_registry.get_model_info(model)
    
class Client:
    def __init__(self, manager: ClientManager, task):
        self.manager = manager
        self.current = manager.current
        self.task = task
        self.history = ChatHistory()
        self.log = logger.bind(src='client', name=self.current.name)

    @property
    def name(self):
        return self.current.name
    
    def use(self, name):
        client = self.manager.get_client(name)
        if client and client.usable():
            self.current = client
            self.log = logger.bind(src='client', name=self.current.name)
            return True
        return False
    
    def has_capability(self, content: LLMContext) -> bool:
        # 判断 content 需要什么能力
        if isinstance(content, str):
            return True
        
        #TODO: 不应该硬编码字符串
        if self.current.kind == 'trust':
            return True
        
        model = self.current.model
        model = model.rsplit('/', 1)[-1]
        model_info = self.manager.get_model_info(model)
        if not model_info:
            self.log.error(f"Model info not found for {model}")
            return False
                
        capabilities = set()
        for item in content:
            if item['type'] == 'image_url':
                capabilities.add(ModelCapability.IMAGE_INPUT)
            if item['type'] == 'file':
                capabilities.add(ModelCapability.FILE_INPUT)
            if item['type'] == 'text':
                capabilities.add(ModelCapability.TEXT)
        
        return any(capability in model_info.capabilities for capability in capabilities)
    
    def __call__(self, content: LLMContext, *, system_prompt=None):
        client = self.current
        stream_processor = StreamProcessor(self.task, client.name)
        msg = client(self.history, content, system_prompt=system_prompt, stream_processor=stream_processor)
        return msg
