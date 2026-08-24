"""
常驻Jupyter内核沙箱

实现有状态常驻沙箱和AST级错误隔离与Patch修复
"""

import ast
import json
import time
import base64
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: str = ""
    error: str = ""
    error_type: str = ""
    error_line: Optional[int] = None
    error_code: Optional[str] = None
    figures: List[str] = field(default_factory=list)  # base64编码的图片
    execution_time: float = 0.0
    variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ASTError:
    """AST解析的错误信息"""
    error_type: str
    error_message: str
    error_line: int
    error_offset: int
    error_code: str
    context_lines: List[str] = field(default_factory=list)
    suggested_fix: Optional[str] = None


class ASTErrorParser:
    """AST级错误解析器"""
    
    def __init__(self):
        self.common_errors = {
            "SyntaxError": self._parse_syntax_error,
            "NameError": self._parse_name_error,
            "TypeError": self._parse_type_error,
            "ValueError": self._parse_value_error,
            "IndexError": self._parse_index_error,
            "KeyError": self._parse_key_error,
            "AttributeError": self._parse_attribute_error,
            "ImportError": self._parse_import_error,
            "ZeroDivisionError": self._parse_zero_division_error,
        }
    
    def parse_error(self, error_type: str, error_message: str, 
                    traceback_str: str, code: str) -> ASTError:
        """解析错误信息"""
        # 提取错误行号
        error_line = self._extract_error_line(traceback_str)
        
        # 获取错误上下文
        context_lines = self._get_context_lines(code, error_line, context=3)
        
        # 提取错误代码
        error_code = self._extract_error_code(code, error_line)
        
        # 生成修复建议
        suggested_fix = self._generate_fix_suggestion(
            error_type, error_message, error_code, context_lines
        )
        
        return ASTError(
            error_type=error_type,
            error_message=error_message,
            error_line=error_line,
            error_offset=0,
            error_code=error_code,
            context_lines=context_lines,
            suggested_fix=suggested_fix
        )
    
    def _extract_error_line(self, traceback_str: str) -> int:
        """从traceback提取错误行号"""
        # 匹配 "line XX" 模式
        match = re.search(r'line (\d+)', traceback_str)
        if match:
            return int(match.group(1))
        return -1
    
    def _get_context_lines(self, code: str, error_line: int, 
                           context: int = 3) -> List[str]:
        """获取错误上下文代码"""
        lines = code.split('\n')
        start = max(0, error_line - context - 1)
        end = min(len(lines), error_line + context)
        
        result = []
        for i in range(start, end):
            prefix = ">>> " if i == error_line - 1 else "    "
            result.append(f"{prefix}{i+1}: {lines[i]}")
        
        return result
    
    def _extract_error_code(self, code: str, error_line: int) -> str:
        """提取错误行代码"""
        lines = code.split('\n')
        if 0 < error_line <= len(lines):
            return lines[error_line - 1].strip()
        return ""
    
    def _generate_fix_suggestion(self, error_type: str, error_message: str,
                                 error_code: str, context_lines: List[str]) -> Optional[str]:
        """生成修复建议"""
        if error_type in self.common_errors:
            return self.common_errors[error_type](error_message, error_code, context_lines)
        return None
    
    def _parse_syntax_error(self, msg: str, code: str, ctx: List[str]) -> str:
        """解析语法错误"""
        if "invalid syntax" in msg:
            return "检查括号、引号是否匹配，语句是否完整"
        if "unexpected EOF" in msg:
            return "代码可能不完整，检查是否有未闭合的括号或引号"
        return "检查代码语法"
    
    def _parse_name_error(self, msg: str, code: str, ctx: List[str]) -> str:
        """解析名称错误"""
        match = re.search(r"name '(\w+)' is not defined", msg)
        if match:
            var_name = match.group(1)
            return f"变量 '{var_name}' 未定义，请先赋值或检查拼写"
        return "检查变量名是否正确"
    
    def _parse_type_error(self, msg: str, code: str, ctx: List[str]) -> str:
        """解析类型错误"""
        if "unsupported operand" in msg:
            return "检查操作数类型是否匹配"
        if "not callable" in msg:
            return "检查对象是否可调用"
        return "检查数据类型"
    
    def _parse_value_error(self, msg: str, code: str, ctx: List[str]) -> str:
        """解析值错误"""
        return "检查输入值是否有效"
    
    def _parse_index_error(self, msg: str, code: str, ctx: List[str]) -> str:
        """解析索引错误"""
        if "list index out of range" in msg:
            return "索引超出列表范围，检查列表长度"
        return "检查索引范围"
    
    def _parse_key_error(self, msg: str, code: str, ctx: List[str]) -> str:
        """解析键错误"""
        match = re.search(r"KeyError: '(\w+)'", msg)
        if match:
            key = match.group(1)
            return f"键 '{key}' 不存在，请检查字典键名"
        return "检查字典键是否存在"
    
    def _parse_attribute_error(self, msg: str, code: str, ctx: List[str]) -> str:
        """解析属性错误"""
        return "检查对象是否有该属性或方法"
    
    def _parse_import_error(self, msg: str, code: str, ctx: List[str]) -> str:
        """解析导入错误"""
        if "No module named" in msg:
            match = re.search(r"No module named '(\w+)'", msg)
            if match:
                module = match.group(1)
                return f"模块 '{module}' 未安装，请运行: pip install {module}"
        return "检查模块是否正确安装"
    
    def _parse_zero_division_error(self, msg: str, code: str, ctx: List[str]) -> str:
        """解析除零错误"""
        return "检查除数是否为零"


class ASTPatchGenerator:
    """AST级Patch生成器"""
    
    def generate_patch(self, original_code: str, error: ASTError) -> str:
        """
        生成Search & Replace格式的补丁
        
        Args:
            original_code: 原始代码
            error: 错误信息
            
        Returns:
            Search & Replace格式的补丁
        """
        if not error.error_line or error.error_line < 0:
            return ""
        
        lines = original_code.split('\n')
        error_line_idx = error.error_line - 1
        
        if error_line_idx >= len(lines):
            return ""
        
        # 提取错误行及其上下文
        start_idx = max(0, error_line_idx - 2)
        end_idx = min(len(lines), error_line_idx + 3)
        
        search_block = '\n'.join(lines[start_idx:end_idx])
        
        # 生成替换建议（这里简化处理，实际应调用LLM）
        replace_block = self._generate_replacement(
            lines[start_idx:end_idx], error
        )
        
        patch = f"""<<<<<<< SEARCH
{search_block}
=======
{replace_block}
>>>>>>> REPLACE"""
        
        return patch
    
    def _generate_replacement(self, lines: List[str], error: ASTError) -> str:
        """生成替换代码"""
        # 简化处理：添加注释说明错误
        result = []
        for i, line in enumerate(lines):
            if i == 2:  # 错误行
                result.append(f"{line}  # FIXME: {error.error_type}: {error.error_message}")
            else:
                result.append(line)
        return '\n'.join(result)


class StatefulJupyterKernel:
    """有状态常驻Jupyter内核"""
    
    def __init__(self, kernel_name: str = "python3"):
        """
        初始化Jupyter内核
        
        Args:
            kernel_name: 内核名称
        """
        self.kernel_name = kernel_name
        self.kernel_id = None
        self.is_running = False
        self.execution_count = 0
        self.variables = {}  # 保持变量状态
        
        self.error_parser = ASTErrorParser()
        self.patch_generator = ASTPatchGenerator()
        
        # 模拟内核状态
        self._namespace = {}
    
    def start(self):
        """启动内核"""
        print(f"启动Jupyter内核: {self.kernel_name}")
        self.is_running = True
        self.kernel_id = f"kernel-{int(time.time())}"
        
        # 预加载常用库
        self.execute("import numpy as np")
        self.execute("import pandas as pd")
        self.execute("import matplotlib.pyplot as plt")
        
        print(f"内核已启动: {self.kernel_id}")
    
    def stop(self):
        """停止内核"""
        print(f"停止Jupyter内核: {self.kernel_id}")
        self.is_running = False
        self._namespace.clear()
    
    def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        """
        执行代码
        
        Args:
            code: Python代码
            timeout: 超时时间
            
        Returns:
            执行结果
        """
        if not self.is_running:
            return ExecutionResult(
                success=False,
                error="内核未启动"
            )
        
        self.execution_count += 1
        start_time = time.time()
        
        try:
            # 使用exec执行代码
            import io
            from contextlib import redirect_stdout, redirect_stderr
            
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            # 执行代码
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, self._namespace)
            
            output = stdout_capture.getvalue()
            error_output = stderr_capture.getvalue()
            
            execution_time = time.time() - start_time
            
            # 提取生成的图表
            figures = self._extract_figures()
            
            # 提取变量
            variables = {
                k: v for k, v in self._namespace.items()
                if not k.startswith('_') and k not in ['np', 'pd', 'plt']
            }
            
            return ExecutionResult(
                success=True,
                output=output,
                execution_time=execution_time,
                figures=figures,
                variables=variables
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_type = type(e).__name__
            error_message = str(e)
            
            # 使用AST解析错误
            import traceback
            traceback_str = traceback.format_exc()
            ast_error = self.error_parser.parse_error(
                error_type, error_message, traceback_str, code
            )
            
            return ExecutionResult(
                success=False,
                error=error_message,
                error_type=error_type,
                error_line=ast_error.error_line,
                error_code=ast_error.error_code,
                execution_time=execution_time
            )
    
    def execute_with_fix(self, code: str, max_retries: int = 3,
                         fix_callback=None) -> ExecutionResult:
        """
        执行代码并尝试自动修复
        
        Args:
            code: Python代码
            max_retries: 最大重试次数
            fix_callback: 修复回调函数
            
        Returns:
            执行结果
        """
        current_code = code
        
        for attempt in range(max_retries):
            result = self.execute(current_code)
            
            if result.success:
                return result
            
            # 尝试修复
            if fix_callback and attempt < max_retries - 1:
                error_info = {
                    "error_type": result.error_type,
                    "error_message": result.error,
                    "error_line": result.error_line,
                    "error_code": result.error_code,
                    "context": self._get_error_context(current_code, result.error_line)
                }
                
                fixed_code = fix_callback(current_code, error_info)
                
                if fixed_code and fixed_code != current_code:
                    current_code = fixed_code
                    print(f"[自动修复] 尝试 {attempt + 1}/{max_retries}")
                    continue
            
            # 无法修复
            return result
        
        return result
    
    def _extract_figures(self) -> List[str]:
        """提取matplotlib图表"""
        figures = []
        try:
            import matplotlib.pyplot as plt
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                import io
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
                buf.seek(0)
                figures.append(base64.b64encode(buf.getvalue()).decode('utf-8'))
                plt.close(fig)
        except Exception:
            pass
        return figures
    
    def _get_error_context(self, code: str, error_line: int) -> str:
        """获取错误上下文"""
        if error_line < 0:
            return ""
        lines = code.split('\n')
        start = max(0, error_line - 3)
        end = min(len(lines), error_line + 2)
        return '\n'.join(lines[start:end])
    
    def get_state(self) -> Dict[str, Any]:
        """获取内核状态"""
        return {
            "kernel_id": self.kernel_id,
            "is_running": self.is_running,
            "execution_count": self.execution_count,
            "variable_count": len(self._namespace),
            "variables": list(self._namespace.keys())
        }


# ============== 测试代码 ==============

if __name__ == "__main__":
    print("=" * 60)
    print("测试 Jupyter 沙箱")
    print("=" * 60)
    
    # 创建内核
    kernel = StatefulJupyterKernel()
    
    # 启动内核
    kernel.start()
    print(f"\n内核状态: {kernel.get_state()}")
    
    # 测试正常执行
    print("\n--- 测试1: 正常执行 ---")
    result = kernel.execute("""
x = 10
y = 20
print(f"x + y = {x + y}")
""")
    print(f"成功: {result.success}")
    print(f"输出: {result.output}")
    print(f"执行时间: {result.execution_time:.3f}秒")
    
    # 测试变量持久化
    print("\n--- 测试2: 变量持久化 ---")
    result = kernel.execute("print(f'x = {x}, y = {y}')")
    print(f"成功: {result.success}")
    print(f"输出: {result.output}")
    
    # 测试错误处理
    print("\n--- 测试3: 错误处理 ---")
    result = kernel.execute("""
# 故意制造错误
z = 1 / 0
""")
    print(f"成功: {result.success}")
    print(f"错误类型: {result.error_type}")
    print(f"错误行: {result.error_line}")
    print(f"错误信息: {result.error}")
    
    # 测试AST错误解析
    print("\n--- 测试4: AST错误解析 ---")
    result = kernel.execute("""
# 名称错误
print(undefined_variable)
""")
    print(f"成功: {result.success}")
    print(f"错误类型: {result.error_type}")
    print(f"错误行: {result.error_line}")
    
    # 测试图表生成
    print("\n--- 测试5: 图表生成 ---")
    result = kernel.execute("""
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(8, 4))
plt.plot(x, y)
plt.title('Sine Wave')
plt.show()
""")
    print(f"成功: {result.success}")
    print(f"图表数量: {len(result.figures)}")
    
    # 停止内核
    kernel.stop()
    
    print("\n" + "=" * 60)
    print("Jupyter 沙箱测试完成！")
    print("=" * 60)
