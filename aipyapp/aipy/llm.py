#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import Counter, defaultdict, namedtuple

from loguru import logger
from rich.live import Live
from rich.text import Text

from .. import T
from .plugin import event_bus
from ..llm import CLIENTS, ChatMessage

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

class LiveManager:
    def __init__(self, name, quiet=False):
        self.live = None
        self.name = name
        self.lr = LineReceiver()
        self.lr_reason = LineReceiver()
        self.title = f"{self.name} {T('Reply')}"
        self.reason_started = False
        self.display_lines = []
        self.max_lines = 10
        self.quiet = quiet

    @property
    def content(self):
        return self.lr.content
    
    @property
    def reason(self):
        return self.lr_reason.content
    
    def __enter__(self):
        if self.quiet: return self
        self.live = Live(auto_refresh=False, vertical_overflow='crop', transient=True)
        self.live.__enter__()
        return self

    def process_chunk(self, content, *, reason=False):
        if not content: return
 
        if not reason and self.lr.empty() and not self.lr_reason.empty():
            line = self.lr_reason.done()
            event_bus.broadcast('response_stream', {'llm': self.name, 'content': f"{line}\n\n----\n\n", 'reason': True})

        lr = self.lr_reason if reason else self.lr
        lines = lr.feed(content)
        if not lines: return

        lines2 = [line for line in lines if not line.startswith('<!-- Block-') and not line.startswith('<!-- Cmd-')]
        if lines2:
            content = '\n'.join(lines2)
            event_bus.broadcast('response_stream', {'llm': self.name, 'content': content, 'reason': reason})

        if self.quiet: return

        if reason and not self.reason_started:
            self.display_lines.append("<think>")
            self.reason_started = True
        elif not reason and self.reason_started:
            self.display_lines.append("</think>")
            self.reason_started = False

        self.display_lines.extend(lines)
        while len(self.display_lines) > self.max_lines:
            self.display_lines.pop(0)
        content = '\n'.join(self.display_lines)
        self.live.update(Text(content, style="dim white"), refresh=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lr.buffer:
            self.process_chunk('\n')
        if self.live:
            self.live.__exit__(exc_type, exc_val, exc_tb)

class ClientManager(object):
    MAX_TOKENS = 8192

    def __init__(self, settings):
        self.clients = {}
        self.default = None
        self.current = None
        self.log = logger.bind(src='client_manager')
        self.names = self._init_clients(settings)

    def _create_client(self, config):
        proto = config.get("type", "openai")
        client = CLIENTS.get(proto.lower())
        if not client:
            self.log.error('Unsupported LLM provider', proto=proto)
            return None
        return client(config)
    
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
    
    def Client(self):
        return Client(self)
    
    def to_records(self):
        LLMRecord = namedtuple('LLMRecord', ['Name', 'Model', 'Max_Tokens', 'Base_URL'])
        rows = []
        for name, client in self.clients.items():
            rows.append(LLMRecord(name, client.model, client.max_tokens, client.base_url))
        return rows
    
class Client:
    def __init__(self, manager: ClientManager):
        self.manager = manager
        self.current = manager.current
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
    
    def __call__(self, instruction, *, system_prompt=None, quiet=False):
        client = self.current
        stream_processor = LiveManager(client.name, quiet=quiet)
        msg = client(self.history, instruction, system_prompt=system_prompt, stream_processor=stream_processor)
        if msg:
            event_bus.broadcast('response_complete', {'llm': client.name, 'content': msg})
        else:
            self.log.error(f"LLM: {client.name} response is None")
        return msg
