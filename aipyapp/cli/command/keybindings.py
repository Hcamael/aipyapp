from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import Completer
from .completer import CompleterContext, PathCompleter

def create_key_bindings(manager):
    """创建键绑定（兼容旧版）"""
    kb = KeyBindings()

    @kb.add('c-f')
    def _(event):
        """按 Ctrl+F 直接进入文件补齐模式"""
        buffer = event.app.current_buffer
        path_completer = PathCompleter()
        
        class TempCompleter(Completer):
            def get_completions(self, document, complete_event):
                text = document.text_before_cursor
                words = text.split()
                context = CompleterContext(
                    text=text,
                    cursor_pos=len(text),
                    words=words,
                    current_word=words[-1] if words and not text.endswith(' ') else "",
                    word_before_cursor=text[:-len(words[-1])] if words and not text.endswith(' ') else text
                )
                return path_completer.get_completions(context)
        
        buffer.completer = TempCompleter()
        buffer.start_completion()

    @kb.add('escape', eager=True)
    def _(event):
        """按ESC恢复默认补齐模式"""
        buffer = event.app.current_buffer
        buffer.completer = manager
        if buffer.complete_state:
            buffer.cancel_completion()
    
    @kb.add('c-t')
    def _(event):
        """按Ctrl+T插入当前时间戳"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        event.app.current_buffer.insert_text(timestamp)
    
    return kb