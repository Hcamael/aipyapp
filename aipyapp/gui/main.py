#!/usr/bin/env python
#coding: utf-8

import os
import sys
import time
import json
import queue
import base64
import mimetypes
import traceback
import threading
from typing import Dict, Any

import wx
import wx.html2
import matplotlib
import matplotlib.pyplot as plt
from loguru import logger
from wx.lib.newevent import NewEvent
from wx.lib.agw.hyperlink import HyperLinkCtrl
from wx import FileDialog, FD_SAVE, FD_OVERWRITE_PROMPT

from .. import __version__, T, get_lang, __respath__
from ..aipy.config import CONFIG_DIR
from ..aipy import TaskManager
from . import ConfigDialog, ApiMarketDialog, show_provider_config, AboutDialog, CStatusBar
from ..config import LLMConfig
from ..display import DisplayManager

ChatEvent, EVT_CHAT = NewEvent()
matplotlib.use('Agg')

def image_to_base64(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        return None

    try:
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        return None

    data_url = f"data:{mime_type};base64,{encoded_string}"
    return data_url

class AIPython(threading.Thread):
    def __init__(self, gui):
        super().__init__(daemon=True)
        self.gui = gui
        self.tm = gui.tm
        self._task = None
        self._busy = threading.Event()
        plt.show = self.plt_show
        sys.modules["matplotlib.pyplot"] = plt
        self.log = logger.bind(src='aipython')

    def stop_task(self):
        if self._task:
            self._task.stop()
        else:
            self.log.warning("没有正在进行的任务")

    def has_task(self):
        return self._task is not None

    def can_done(self):
        return not self._busy.is_set() and self.has_task()

    def plt_show(self, *args, **kwargs):
        filename = f'{time.strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(filename)
        user = 'BB-8'
        content = f'![{filename}]({filename})'
        evt = ChatEvent(user=user, msg=content)
        wx.PostEvent(self.gui, evt)

    def on_show_image(self, event):
        user = T("Turing")
        if event.data['path']:
            base64_data = image_to_base64(event.data['path'])
            content = base64_data if base64_data else event.data['path']
        else:
            content = event.data['url']

        msg = f'![图片]({content})'
        evt = ChatEvent(user=user, msg=msg)
        wx.PostEvent(self.gui, evt)

    def on_stream(self, event):
        user = T("Turing")
        content = '\n'.join(event.data['lines'])
        evt = ChatEvent(user=user, msg=content)
        wx.PostEvent(self.gui, evt)

    def on_round_end(self, event):
        user = T("AIPy")
        summary = event.data.get('summary')
        evt = ChatEvent(user=user, msg=f'{T("End processing instruction")} {summary.get("summary")}')
        wx.PostEvent(self.gui, evt)

    def on_exec(self, event ):
        user = 'BB-8'
        content = f"```{event.data['block'].lang}\n{event.data['block'].code}\n```"
        evt = ChatEvent(user=user, msg=content)
        wx.PostEvent(self.gui, evt)

    def on_exec_result(self, event):
        user = 'BB-8'
        result = event.data.get('result')
        content = json.dumps(result, indent=4, ensure_ascii=False)
        content = f'{T("Run result")}\n```json\n{content}\n```'
        evt = ChatEvent(user=user, msg=content)
        wx.PostEvent(self.gui, evt)

    def run(self):
        while True:
            instruction = self.gui.get_task()
            if instruction in ('/done', 'done'):
                if self._task:
                    self._task.done()
                    self._task = None
                else:
                    self.log.warning("没有正在进行的任务")
                wx.CallAfter(self.gui.on_task_done)
            elif instruction in ('/exit', 'exit'):
                break
            else:
                self._busy.set()
                try:
                    if not self._task:
                        self._task = self.tm.new_task()
                        self._task.register_listener(self)
                    self._task.run(instruction)
                except Exception as e:
                    self.log.exception('Error running task')
                finally:
                    self._busy.clear()
                wx.CallAfter(self.gui.toggle_input)

class FileDropTarget(wx.FileDropTarget):
    def __init__(self, text_ctrl, gui_frame):
        super().__init__()
        self.text_ctrl = text_ctrl
        self.gui_frame = gui_frame

    def OnDropFiles(self, x, y, filenames):
        # 直接在光标处插入@文件路径
        current_text = self.text_ctrl.GetValue()
        cursor_pos = self.text_ctrl.GetInsertionPoint()
        insert_text = ' '.join([f"@{f}" for f in filenames])
        new_text = current_text[:cursor_pos] + insert_text + current_text[cursor_pos:]
        self.text_ctrl.SetValue(new_text)
        self.text_ctrl.SetInsertionPoint(cursor_pos + len(insert_text))
        wx.MessageBox(f"已添加 {len(filenames)} 个文件: {', '.join(filenames)}", "文件添加成功")
        return True

class ChatFrame(wx.Frame):
    def __init__(self, tm):
        title = T("🐙 AIPY - Your AI Assistant 🐂 🐎")
        super().__init__(None, title=title, size=(1024, 768))
        
        self.tm = tm
        self.title = title
        self.log = logger.bind(src='gui')
        self.task_queue = queue.Queue()
        self.aipython = AIPython(self)
        self.welcomed = False  # 添加初始化标志
        self.html_file_path = os.path.abspath(__respath__ / f"chatroom_{get_lang()}.html")
        self.avatars = {T("Me"): '🧑', 'BB-8': '🤖', T("Turing"): '🧠', T("AIPy"): '🐙'}

        icon = wx.Icon(str(__respath__ / "aipy.ico"), wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        self.make_menu_bar()
        self.make_panel()
        self.statusbar = CStatusBar(self)
        self.SetStatusBar(self.statusbar)
        self.statusbar.SetStatusText(T("Press Ctrl/Cmd+Enter to send message"), 0)

        self.Bind(EVT_CHAT, self.on_chat)
        self.webview.Bind(wx.html2.EVT_WEBVIEW_TITLE_CHANGED, self.on_webview_title_changed)
        self.aipython.start()
        self.Show()

    def make_input_panel(self, panel):
        self.container = wx.Panel(panel)
 
        self.input = wx.TextCtrl(self.container, style=wx.TE_MULTILINE)
        self.input.SetMinSize((-1, 60))
        self.input.SetWindowStyleFlag(wx.BORDER_SIMPLE)
        self.input.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.done_button = wx.Button(self.container, label=T("End"), size=(50, -1))
        self.done_button.Hide()
        self.done_button.Bind(wx.EVT_BUTTON, self.on_done)
        self.send_button = wx.Button(self.container, label=T("Send"), size=(50, -1))
        self.send_button.Bind(wx.EVT_BUTTON, self.on_send)
        self.container.Bind(wx.EVT_SIZE, self.on_container_resize)
        return self.container

    def make_input_panel2(self, panel):
        container = wx.Panel(panel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.input = wx.TextCtrl(container, style=wx.TE_MULTILINE)
        self.input.SetMinSize((-1, 80))
        self.input.SetWindowStyleFlag(wx.BORDER_SIMPLE)
        self.input.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        hbox.Add(self.input, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.done_button = wx.Button(container, label=T("End"))
        self.done_button.Hide()
        self.done_button.Bind(wx.EVT_BUTTON, self.on_done)
        self.done_button.SetBackgroundColour(wx.Colour(255, 230, 230)) 
        self.send_button = wx.Button(container, label=T("Send"))
        self.send_button.Bind(wx.EVT_BUTTON, self.on_send)
        vbox.Add(self.done_button, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vbox.AddSpacer(10)
        vbox.Add(self.send_button, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        hbox.Add(vbox, 0, wx.ALIGN_CENTER)
        container.SetSizer(hbox)    
        self.container = container
        return container
    
    def make_panel(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.webview = wx.html2.WebView.New(panel)
        self.webview.LoadURL(f'file://{self.html_file_path}')
        self.webview.SetWindowStyleFlag(wx.BORDER_NONE)
        vbox.Add(self.webview, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)

        if sys.platform == 'darwin':
            input_panel = self.make_input_panel(panel)
        else:
            input_panel = self.make_input_panel2(panel)
        drop_target = FileDropTarget(self.input, self)
        self.input.SetDropTarget(drop_target)
        font = wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.input.SetFont(font)
        self.input.SetFocus()
    
        vbox.Add(input_panel, proportion=0, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=12)

        panel.SetSizer(vbox)
        self.panel = panel

    def make_menu_bar(self):
        menubar = wx.MenuBar()
        
        # 文件菜单
        file_menu = wx.Menu()
        save_item = file_menu.Append(wx.ID_SAVE, T("Save chat history as HTML"))
        clear_item = file_menu.Append(wx.ID_CLEAR, T("Clear chat"))
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, T("Exit"))
        menubar.Append(file_menu, T("File"))
        
        # 编辑菜单
        edit_menu = wx.Menu()
        config_item = edit_menu.Append(wx.ID_ANY, T("Configuration"))
        api_market_item = edit_menu.Append(wx.ID_ANY, T("API Market"))
        menubar.Append(edit_menu, T("Edit"))
        
        # 任务菜单
        task_menu = wx.Menu()
        self.new_task_item = task_menu.Append(wx.ID_NEW, T("Start new task"))
        self.stop_task_item = task_menu.Append(wx.ID_ANY, T("Stop task"))
        self.stop_task_item.Enable(False)
        self.Bind(wx.EVT_MENU, self.on_stop_task, self.stop_task_item)
        self.share_task_item = task_menu.Append(wx.ID_ANY, T("Share task"))
        self.share_task_item.Enable(False)
        self.Bind(wx.EVT_MENU, self.on_share_task, self.share_task_item)
        menubar.Append(task_menu, T("Task"))

        # 帮助菜单
        help_menu = wx.Menu()
        website_item = help_menu.Append(wx.ID_ANY, T("Website"))
        #forum_item = help_menu.Append(wx.ID_ANY, T('Forum'))
        if get_lang() == 'zh':
            wechat_item = help_menu.Append(wx.ID_ANY, T("WeChat Group"))
            self.Bind(wx.EVT_MENU, self.on_open_website, wechat_item)
        help_menu.AppendSeparator()
        about_item = help_menu.Append(wx.ID_ABOUT, T("About"))
        menubar.Append(help_menu, T("Help"))
        
        self.SetMenuBar(menubar)
        
        # 绑定事件
        self.Bind(wx.EVT_MENU, self.on_save_html, save_item)
        self.Bind(wx.EVT_MENU, self.on_clear_chat, clear_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_MENU, self.on_done, self.new_task_item)
        self.Bind(wx.EVT_MENU, self.on_config, config_item)
        self.Bind(wx.EVT_MENU, self.on_api_market, api_market_item)
        self.Bind(wx.EVT_MENU, self.on_open_website, website_item)
        #self.Bind(wx.EVT_MENU, self.on_open_website, forum_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)

    def on_exit(self, event):
        self.task_queue.put('exit')
        self.aipython.join()
        self.Close()

    def on_stop_task(self, event):
        self.aipython.stop_task()

    def on_done(self, event):
        self.task_queue.put('/done')
        
    def on_task_done(self):
        self.done_button.Hide()
        self.SetStatusText(T("Current task has ended"), 0)
        self.new_task_item.Enable(False)
        self.SetTitle(self.title)
        self.clear_chat()

    def on_container_resize(self, event):
        container_size = event.GetSize()
        self.input.SetSize(container_size)

        overlap = -20
        send_button_size = self.send_button.GetSize()
        button_pos_x = container_size.width - send_button_size.width + overlap
        button_pos_y = container_size.height - send_button_size.height - 10
        self.send_button.SetPosition((button_pos_x, button_pos_y))

        if self.aipython.can_done():
            done_button_size = self.done_button.GetSize()
            button_pos_x = container_size.width - done_button_size.width + overlap
            button_pos_y = 10
            self.done_button.SetPosition((button_pos_x, button_pos_y))
            self.done_button.Show()

        event.Skip()

    def on_clear_chat(self, event):
        self.webview.LoadURL(f'file://{self.html_file_path}')

    def clear_chat(self):
        """清空聊天记录"""
        js_code = """
        const chatContainer = document.querySelector('.chat-container');
        chatContainer.innerHTML = '';
        lastUser = '';
        lastMessage = null;
        lastRawContent = '';
        """
        self.webview.RunScript(js_code)

    def on_open_website(self, event):
        """打开网站"""
        menu_item = self.GetMenuBar().FindItemById(event.GetId())
        if not menu_item:
            return
            
        label = menu_item.GetItemLabel()
        if label == T("Website"):
            url = T("https://aipy.app")
        elif label == T("Forum"):
            url = T("https://d.aipy.app")
        elif label == T("WeChat Group"):
            url = T("https://d.aipy.app/d/13")
        else:
            return
        wx.LaunchDefaultBrowser(url)

    def on_about(self, event):
        about_dialog = AboutDialog(self)
        about_dialog.ShowModal()
        about_dialog.Destroy()

    def on_save_html(self, event):
        try:
            html_content = self.webview.GetPageSource()
            self.save_html_content(html_content)
        except Exception as e:
            wx.MessageBox(f"save html error: {e}", "Error")

    def save_html_content(self, html_content):
        with FileDialog(self, T("Save chat history as HTML file"), wildcard="HTML file (*.html)|*.html",
                        style=FD_SAVE | FD_OVERWRITE_PROMPT) as dialog:
            if dialog.ShowModal() == wx.ID_CANCEL:
                return

            path = dialog.GetPath()
            try:
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(html_content)
            except IOError:
                wx.LogError(f"{T('Failed to save file')}: {path}")

    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        send_shortcut = (event.ControlDown() or event.CmdDown()) and keycode == wx.WXK_RETURN

        if send_shortcut:
            self.send_message()
        else:
            event.Skip()

    def on_send(self, event):
        self.send_message()

    def get_task(self):
        return self.task_queue.get()

    def toggle_input(self):
        if self.container.IsShown():
            self.container.Hide()
            self.done_button.Hide()
            wx.BeginBusyCursor()
            self.SetStatusText(T("Operation in progress, please wait..."), 0)
            self.new_task_item.Enable(False)
            self.stop_task_item.Enable(True)
            self.share_task_item.Enable(False)
        else:
            self.container.Show()
            self.done_button.Show()
            wx.EndBusyCursor()
            self.SetStatusText(T("Operation completed. If you start a new task, please click the `End` button"), 0)
            self.new_task_item.Enable(self.aipython.can_done())
            self.stop_task_item.Enable(False)
            self.share_task_item.Enable(True)

        self.panel.Layout()
        self.panel.Refresh()

    def send_message(self):
        text = self.input.GetValue().strip()
        if not text:
            return
        
        if not self.aipython.has_task():
            self.SetTitle(f"[{T('Current task')}] {text}")

        self.append_message(T("Me"), text)
        self.input.Clear()
        
        self.toggle_input()
        self.task_queue.put(text)

    def on_chat(self, event):
        user = event.user
        text = event.msg
        self.append_message(user, text)

    def append_message(self, user, text):
        avatar = self.avatars[user]
        js_code = f'appendMessage("{avatar}", "{user}", {repr(text)});'
        self.webview.RunScript(js_code)

    def on_config(self, event):
        dialog = ConfigDialog(self, self.tm.settings)
        if dialog.ShowModal() == wx.ID_OK:
            values = dialog.get_values()
            if values['timeout'] == 0:
                del values['timeout']
            self.tm.config_manager.update_sys_config(values)
        dialog.Destroy()

    def on_api_market(self, event):
        """打开API配置对话框"""
        dialog = ApiMarketDialog(self, self.tm.config_manager)
        dialog.ShowModal()
        dialog.Destroy()

    def on_llm_config(self, event):
        """打开LLM配置向导"""
        show_provider_config(self.tm.llm_config, parent=self)

    def on_webview_title_changed(self, event):
        """WebView 标题改变时的处理"""
        if not self.welcomed:
            wx.CallLater(100, self.append_message, T("AIPy"), T("""Hello! I am **AIPy**, your intelligent task assistant!
Please allow me to introduce the other members of the team:
- Turing: The strongest artificial intelligence, complex task analysis and planning
- BB-8: The strongest robot, responsible for executing tasks

Note: Click the "**Help**" link in the menu bar to contact the **AIPy** official and join the group chat."""))
            self.welcomed = True

            # 检查更新
            try:
                update = self.tm.get_update()
                if update and update.get('has_update'):
                    wx.CallLater(1000, self.append_message, T("AIPy"), f"\n🔔 **{T('Update available')}❗**: `v{update.get('latest_version')}`")
            except Exception as e:
                self.log.error(f"检查更新时出错: {e}")
            
        event.Skip()

    def on_share_task(self, event):
        """分享当前任务记录"""
        try:
            html_content = self.webview.GetPageSource()
            result = self.tm.diagnose.report_data(html_content, 'task_record.html')
            self.log.info(f"分享任务记录: {result}")
            if result.get('success'):
                dialog = ShareResultDialog(self, result['url'])
                dialog.ShowModal()
                dialog.Destroy()
            else:
                dialog = ShareResultDialog(self, None, result.get('error'))
                dialog.ShowModal()
                dialog.Destroy()
        except Exception as e:
            dialog = ShareResultDialog(self, None, str(e))
            dialog.ShowModal()
            dialog.Destroy()

class ShareResultDialog(wx.Dialog):
    def __init__(self, parent, url, error=None):
        super().__init__(parent, title=T("Share result"), size=(400, 200))
        logger.info(f"ShareResultDialog: {url}, {error}")
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        if error:
            # 显示错误信息
            error_text = wx.StaticText(self, label=T("Share failed"))
            error_text.SetForegroundColour(wx.Colour(255, 0, 0))
            vbox.Add(error_text, 0, wx.ALL | wx.ALIGN_CENTER, 10)
            
            error_msg = wx.StaticText(self, label=error)
            error_msg.Wrap(350)
            vbox.Add(error_msg, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        else:
            # 显示成功信息
            success_text = wx.StaticText(self, label=T("Share success"))
            success_text.SetForegroundColour(wx.Colour(0, 128, 0))
            vbox.Add(success_text, 0, wx.ALL | wx.ALIGN_CENTER, 10)
            
            # 添加提示文本
            hint_text = wx.StaticText(self, label=T("Click the link below to view the task record"))
            vbox.Add(hint_text, 0, wx.ALL | wx.ALIGN_CENTER, 5)
            
            # 添加可点击的链接
            link = HyperLinkCtrl(self, -1, T("View task record"), URL=url)
            link.EnableRollover(True)
            link.SetUnderlines(False, False, True)
            vbox.Add(link, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        
        # 添加确定按钮
        ok_button = wx.Button(self, wx.ID_OK, T("OK"))
        vbox.Add(ok_button, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        self.SetSizer(vbox)
        self.Centre()


def main(settings):
    app = wx.App(False)
    llm_config = LLMConfig(CONFIG_DIR / "config")
    if settings.get('llm_need_config'):
        if llm_config.need_config():
            show_provider_config(llm_config)
            if llm_config.need_config():
                return
        settings["llm"] = llm_config.config
        
    # 初始化显示效果管理器
    display_config = settings.get('display', {})
    display_manager = DisplayManager(display_config)

    try:
        tm = TaskManager(settings, display_manager=display_manager)
    except Exception as e:
        traceback.print_exc()
        return
    tm.config_manager = settings['config_manager']
    tm.llm_config = llm_config
    ChatFrame(tm)
    app.MainLoop()
