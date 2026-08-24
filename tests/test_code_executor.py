"""
代码执行器单元测试
"""

import pytest
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.code_executor import CodeExecutor, SafeCodeExecutor


class TestCodeExecutor:
    """CodeExecutor测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.executor = CodeExecutor(timeout=10)
    
    def test_basic_execution(self):
        """测试基本代码执行"""
        code = "x = 1 + 2\nprint(x)"
        result = self.executor.execute(code)
        
        assert result['success'] is True
        assert "3" in result['stdout']
    
    def test_variable_in_same_execution(self):
        """测试同一次执行中的变量"""
        code = "x = 10\nprint(x)"
        result = self.executor.execute(code)
        
        assert result['success'] is True
        assert "10" in result['stdout']
    
    def test_error_handling(self):
        """测试错误处理"""
        code = "1 / 0"
        result = self.executor.execute(code)
        
        assert result['success'] is False
        assert "division by zero" in result['stderr'] or "ZeroDivisionError" in result['stderr']
    
    def test_syntax_error(self):
        """测试语法错误"""
        code = "def f("
        result = self.executor.execute(code)
        
        assert result['success'] is False
        assert "SyntaxError" in result['stderr']
    
    def test_name_error(self):
        """测试名称错误"""
        code = "print(undefined_variable)"
        result = self.executor.execute(code)
        
        assert result['success'] is False
        assert "NameError" in result['stderr']
    
    def test_matplotlib_code(self):
        """测试matplotlib代码执行"""
        code = """
import matplotlib.pyplot as plt
plt.figure()
plt.plot([1, 2, 3], [1, 2, 3])
plt.show()
"""
        result = self.executor.execute(code)
        
        assert result['success'] is True
    
    def test_output_capture(self):
        """测试输出捕获"""
        code = "print('Hello')\nprint('World')"
        result = self.executor.execute(code)
        
        assert result['success'] is True
        assert "Hello" in result['stdout']
        assert "World" in result['stdout']
    
    def test_variables_returned(self):
        """测试变量返回"""
        code = "x = 42\ny = 'hello'"
        result = self.executor.execute(code)
        
        assert result['success'] is True
        assert 'variables' in result


class TestSafeCodeExecutor:
    """SafeCodeExecutor测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.executor = SafeCodeExecutor(timeout=10)
    
    def test_safe_code(self):
        """测试安全代码"""
        code = "x = 1 + 2"
        result = self.executor.execute(code)
        
        assert result['success'] is True
    
    def test_dangerous_import(self):
        """测试危险导入"""
        code = "import os"
        result = self.executor.execute(code)
        
        assert result['success'] is False
        assert "安全检查未通过" in result['stderr']
    
    def test_dangerous_function(self):
        """测试危险函数"""
        code = "eval('1+1')"
        result = self.executor.execute(code)
        
        assert result['success'] is False
        assert "安全检查未通过" in result['stderr']
    
    def test_safe_imports(self):
        """测试安全导入"""
        code = "import numpy as np\nimport pandas as pd"
        result = self.executor.execute(code)
        
        assert result['success'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
