"""
MathModelAgent TUI 界面

基于Textual的终端用户界面
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Static, Input, Button, 
    DataTable, Log, ProgressBar, TabbedContent, TabPane
)
from textual.reactive import reactive
from textual.message import Message
from textual import on, work
from rich.text import Text
from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown
import asyncio
from datetime import datetime
from typing import Optional


class ThinkingIndicator(Static):
    """思考指示器"""
    
    def on_mount(self) -> None:
        self.set_interval(0.3, self.update_animation)
        self.dots = 0
    
    def update_animation(self) -> None:
        self.dots = (self.dots + 1) % 4
        self.update(f"[bold blue]思考{'.' * self.dots}[/]")


class ToolCallWidget(Static):
    """工具调用显示组件"""
    
    def __init__(self, tool_name: str, arguments: str, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.arguments = arguments
    
    def compose(self) -> ComposeResult:
        yield Static(
            f"[bold yellow]🔧 调用工具:[/] [cyan]{self.tool_name}[/]\n"
            f"[dim]参数: {self.arguments}[/]"
        )


class ToolResultWidget(Static):
    """工具结果显示组件"""
    
    def __init__(self, tool_name: str, result: str, success: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.result = result
        self.success = success
    
    def compose(self) -> ComposeResult:
        status = "[green]✓ 成功[/]" if self.success else "[red]✗ 失败[/]"
        yield Static(
            f"[bold yellow]📋 工具结果:[/] [cyan]{self.tool_name}[/] {status}\n"
            f"[dim]{self.result[:200]}{'...' if len(self.result) > 200 else ''}[/]"
        )


class MessageWidget(Static):
    """消息显示组件"""
    
    def __init__(self, role: str, content: str, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content = content
    
    def compose(self) -> ComposeResult:
        if self.role == "user":
            prefix = "[bold green]👤 用户:[/]"
        elif self.role == "assistant":
            prefix = "[bold blue]🤖 助手:[/]"
        else:
            prefix = "[bold yellow]⚙️ 系统:[/]"
        
        yield Static(f"{prefix}\n{self.content}")


class ChatPanel(Static):
    """聊天面板"""
    
    def compose(self) -> ComposeResult:
        yield Static("[bold]💬 对话历史[/]", id="chat-header")
        yield Container(id="chat-messages")
    
    def add_message(self, role: str, content: str):
        """添加消息"""
        container = self.query_one("#chat-messages")
        widget = MessageWidget(role, content)
        container.mount(widget)
        widget.scroll_visible()
    
    def add_tool_call(self, tool_name: str, arguments: str):
        """添加工具调用"""
        container = self.query_one("#chat-messages")
        widget = ToolCallWidget(tool_name, arguments)
        container.mount(widget)
        widget.scroll_visible()
    
    def add_tool_result(self, tool_name: str, result: str, success: bool = True):
        """添加工具结果"""
        container = self.query_one("#chat-messages")
        widget = ToolResultWidget(tool_name, result, success)
        container.mount(widget)
        widget.scroll_visible()
    
    def show_thinking(self):
        """显示思考状态"""
        container = self.query_one("#chat-messages")
        widget = ThinkingIndicator()
        widget.id = "thinking-indicator"
        container.mount(widget)
        widget.scroll_visible()
    
    def hide_thinking(self):
        """隐藏思考状态"""
        try:
            widget = self.query_one("#thinking-indicator")
            widget.remove()
        except Exception:
            pass


class StatusBar(Static):
    """状态栏"""
    
    status = reactive("就绪")
    task_count = reactive(0)
    memory_count = reactive(0)
    
    def render(self) -> Text:
        return Text.from_markup(
            f"[bold]状态:[/] {self.status}  |  "
            f"[bold]任务:[/] {self.task_count}  |  "
            f"[bold]记忆:[/] {self.memory_count}"
        )


class MetricsPanel(Static):
    """指标面板"""
    
    def compose(self) -> ComposeResult:
        yield Static("[bold]📊 系统指标[/]", id="metrics-header")
        yield DataTable(id="metrics-table")
    
    def on_mount(self) -> None:
        table = self.query_one("#metrics-table")
        table.add_columns("指标", "值")
        table.add_rows([
            ("总任务数", "0"),
            ("成功任务", "0"),
            ("任务成功率", "0%"),
            ("代码执行次数", "0"),
            ("RAG检索次数", "0"),
            ("平均响应时间", "0秒"),
        ])
    
    def update_metrics(self, metrics: dict):
        """更新指标"""
        table = self.query_one("#metrics-table")
        table.clear()
        table.add_rows([
            ("总任务数", str(metrics.get("total_tasks", 0))),
            ("成功任务", str(metrics.get("successful_tasks", 0))),
            ("任务成功率", f"{metrics.get('success_rate', 0):.1%}"),
            ("代码执行次数", str(metrics.get("code_executions", 0))),
            ("RAG检索次数", str(metrics.get("rag_queries", 0))),
            ("平均响应时间", f"{metrics.get('avg_response_time', 0):.2f}秒"),
        ])


class InputPanel(Static):
    """输入面板"""
    
    def compose(self) -> ComposeResult:
        yield Input(placeholder="输入消息...", id="user-input")
        yield Horizontal(
            Button("发送", id="send-btn", variant="primary"),
            Button("清空", id="clear-btn"),
            Button("退出", id="quit-btn", variant="error"),
        )
    
    @on(Button.Pressed, "#send-btn")
    def on_send(self):
        input_widget = self.query_one("#user-input")
        if input_widget.value:
            self.post_message(InputPanel.SendPressed(input_widget.value))
            input_widget.value = ""
    
    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted):
        if event.value:
            self.post_message(InputPanel.SendPressed(event.value))
            self.query_one("#user-input").value = ""
    
    @on(Button.Pressed, "#clear-btn")
    def on_clear(self):
        self.post_message(InputPanel.ClearPressed())
    
    @on(Button.Pressed, "#quit-btn")
    def on_quit(self):
        self.post_message(InputPanel.QuitPressed())
    
    class SendPressed(Message):
        def __init__(self, content: str):
            super().__init__()
            self.content = content
    
    class ClearPressed(Message):
        pass
    
    class QuitPressed(Message):
        pass


class MathModelAgentTUI(App):
    """MathModelAgent TUI 应用"""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 2;
        grid-columns: 2fr 1fr;
        grid-rows: 1fr auto;
    }
    
    #chat-panel {
        row-span: 2;
        border: solid $primary;
        height: 100%;
    }
    
    #metrics-panel {
        border: solid $secondary;
        height: 1fr;
    }
    
    #memory-panel {
        border: solid $accent;
        height: 1fr;
    }
    
    #input-panel {
        column-span: 3;
        height: auto;
        dock: bottom;
    }
    
    #chat-messages {
        height: 1fr;
        overflow-y: auto;
    }
    
    #user-input {
        width: 1fr;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        ("ctrl+c", "quit", "退出"),
        ("ctrl+l", "clear", "清空"),
        ("ctrl+s", "send", "发送"),
    ]
    
    def __init__(self):
        super().__init__()
        self.chat_history = []
        self.is_thinking = False
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container(id="chat-panel"):
            yield ChatPanel()
        
        with Container(id="metrics-panel"):
            yield MetricsPanel()
        
        with Container(id="memory-panel"):
            yield Static("[bold]🧠 记忆状态[/]\n\n温记忆: 0\n热记忆: 0\n冷记忆: 0")
        
        yield InputPanel()
        yield Footer()
    
    @on(InputPanel.SendPressed)
    def on_send_message(self, event: InputPanel.SendPressed):
        """处理发送消息"""
        content = event.content
        chat_panel = self.query_one(ChatPanel)
        
        # 添加用户消息
        chat_panel.add_message("user", content)
        self.chat_history.append({"role": "user", "content": content})
        
        # 模拟Agent响应
        self.process_message(content)
    
    @on(InputPanel.ClearPressed)
    def on_clear(self):
        """清空聊天"""
        self.action_clear()
    
    @on(InputPanel.QuitPressed)
    def on_quit(self):
        """退出应用"""
        self.action_quit()
    
    @work(exclusive=True)
    async def process_message(self, content: str):
        """处理消息（异步）"""
        chat_panel = self.query_one(ChatPanel)
        status_bar = self.query_one(StatusBar)
        
        # 显示思考状态
        chat_panel.show_thinking()
        status_bar.status = "思考中..."
        
        # 模拟延迟
        await asyncio.sleep(1)
        
        # 模拟工具调用
        chat_panel.hide_thinking()
        chat_panel.add_tool_call("knowledge_search", f'{{"query": "{content}"}}')
        
        await asyncio.sleep(0.5)
        chat_panel.add_tool_result("knowledge_search", "找到3条相关知识", True)
        
        # 模拟响应
        await asyncio.sleep(1)
        response = f"这是对'{content}'的响应。我正在分析您的问题..."
        chat_panel.add_message("assistant", response)
        self.chat_history.append({"role": "assistant", "content": response})
        
        # 更新状态
        status_bar.status = "就绪"
        status_bar.task_count += 1
    
    def action_clear(self):
        """清空聊天历史"""
        chat_panel = self.query_one(ChatPanel)
        container = chat_panel.query_one("#chat-messages")
        container.remove_children()
        self.chat_history = []
    
    def action_quit(self):
        """退出应用"""
        self.exit()


if __name__ == "__main__":
    app = MathModelAgentTUI()
    app.run()
