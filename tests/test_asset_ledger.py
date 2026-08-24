"""
资产账本单元测试
"""

import pytest
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.asset_ledger import AssetLedger


class TestAssetLedger:
    """AssetLedger测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.ledger_path = Path(self.temp_dir) / "test_artifacts.json"
        self.ledger = AssetLedger(str(self.ledger_path))
    
    def teardown_method(self):
        """测试后清理"""
        if self.ledger_path.exists():
            self.ledger_path.unlink()
    
    def test_add_scalar(self):
        """测试添加标量"""
        record = self.ledger.add_scalar("R2", 0.95, source="test")
        
        assert record.key == "R2"
        assert record.value == 0.95
        assert record.asset_type == "scalar"
    
    def test_add_figure(self):
        """测试添加图表"""
        record = self.ledger.add_figure("plot", "./test.png", source="test")
        
        assert record.key == "plot"
        assert record.asset_type == "figure"
    
    def test_add_table(self):
        """测试添加表格"""
        data = [{"a": 1, "b": 2}]
        record = self.ledger.add_table("table", data, source="test")
        
        assert record.key == "table"
        assert record.asset_type == "table"
    
    def test_get_value(self):
        """测试获取值"""
        self.ledger.add_scalar("value", 42)
        
        assert self.ledger.get_value("value") == 42
    
    def test_get_nonexistent(self):
        """测试获取不存在的资产"""
        assert self.ledger.get("nonexistent") is None
        assert self.ledger.get_value("nonexistent") is None
    
    def test_persistence(self):
        """测试持久化"""
        self.ledger.add_scalar("persist", 100)
        
        # 重新加载
        new_ledger = AssetLedger(str(self.ledger_path))
        assert new_ledger.get_value("persist") == 100
    
    def test_summary(self):
        """测试摘要"""
        self.ledger.add_scalar("a", 1)
        self.ledger.add_figure("b", "./test.png")
        
        summary = self.ledger.summary()
        
        assert summary['total_assets'] == 2
        assert summary['type_counts']['scalar'] == 1
        assert summary['type_counts']['figure'] == 1
    
    def test_delete(self):
        """测试删除"""
        self.ledger.add_scalar("to_delete", 1)
        result = self.ledger.delete("to_delete")
        
        assert result is True
        assert self.ledger.get("to_delete") is None
    
    def test_clear(self):
        """测试清空"""
        self.ledger.add_scalar("a", 1)
        self.ledger.add_scalar("b", 2)
        
        self.ledger.clear()
        
        assert self.ledger.summary()['total_assets'] == 0
    
    def test_typst_macros(self):
        """测试Typst宏生成"""
        self.ledger.add_scalar("R2", 0.95)
        self.ledger.add_figure("plot", "./test.png")
        
        macros = self.ledger.to_typst_macros()
        
        assert 'R2' in macros
        assert 'plot' in macros
    
    def test_typst_injection(self):
        """测试Typst注入"""
        self.ledger.add_scalar("loss", 0.01)
        
        template = 'Loss: #metric("loss")'
        result = self.ledger.inject_typst(template)
        
        assert "0.0100" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
