"""
MathModelAgent 核心模块

包含以下模块：
- code_executor: 代码执行器
- template_manager: 模板管理器
- task_boundary: 任务边界管理
- session_manager: 会话管理
- context_manager: 上下文管理
- logger: 日志系统
- evaluator: 评估器
"""

from .code_executor import CodeExecutor, SafeCodeExecutor
from .template_manager import TemplateManager, CumcmTemplate, McmIcmTemplate
from .task_boundary import TaskBoundaryManager, TaskBoundary, TaskStatus
from .session_manager import SessionManager, Session, SessionEvent, EventType
from .context_manager import ContextManager, ContextWindow, ArchiveEntry
from .logger import Logger, PerformanceLogger, get_logger, get_performance_logger
from .evaluator import AgentEvaluator

__version__ = "1.0.0"
__author__ = "16deng"

__all__ = [
    # 代码执行
    "CodeExecutor",
    "SafeCodeExecutor",
    
    # 模板管理
    "TemplateManager",
    "CumcmTemplate",
    "McmIcmTemplate",
    
    # 任务边界
    "TaskBoundaryManager",
    "TaskBoundary",
    "TaskStatus",
    
    # 会话管理
    "SessionManager",
    "Session",
    "SessionEvent",
    "EventType",
    
    # 上下文管理
    "ContextManager",
    "ContextWindow",
    "ArchiveEntry",
    
    # 日志系统
    "Logger",
    "PerformanceLogger",
    "get_logger",
    "get_performance_logger",
    
    # 评估器
    "AgentEvaluator",
]
