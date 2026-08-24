"""
数据画像单元测试
"""

import pytest
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_profiler import DataProfiler, ModelRouter


class TestDataProfiler:
    """DataProfiler测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.profiler = DataProfiler()
        
        # 创建测试数据
        np.random.seed(42)
        self.df = pd.DataFrame({
            'id': range(100),
            'value': np.random.randn(100),
            'category': np.random.choice(['A', 'B', 'C'], 100)
        })
    
    def test_profile_shape(self):
        """测试数据形状"""
        profile = self.profiler.profile_dataframe(self.df)
        
        assert profile.shape == (100, 3)
    
    def test_profile_columns(self):
        """测试列信息"""
        profile = self.profiler.profile_dataframe(self.df)
        
        assert len(profile.columns) == 3
        assert profile.columns[0]['name'] == 'id'
    
    def test_profile_statistics(self):
        """测试统计信息"""
        profile = self.profiler.profile_dataframe(self.df)
        
        assert 'id' in profile.statistics
        assert 'value' in profile.statistics
    
    def test_profile_missing_rates(self):
        """测试缺失率"""
        # 添加缺失值
        df = self.df.copy()
        df.loc[0:9, 'value'] = np.nan
        
        profile = self.profiler.profile_dataframe(df)
        
        assert profile.missing_rates['value'] == 10.0
    
    def test_profile_sample_data(self):
        """测试样例数据"""
        profile = self.profiler.profile_dataframe(self.df)
        
        assert len(profile.sample_data) == 5
    
    def test_token_estimate(self):
        """测试Token估算"""
        profile = self.profiler.profile_dataframe(self.df)
        
        assert profile.token_estimate > 0
    
    def test_to_prompt(self):
        """测试Prompt生成"""
        profile = self.profiler.profile_dataframe(self.df)
        prompt = profile.to_prompt()
        
        assert "数据概览" in prompt
        assert "列信息" in prompt
        assert "统计摘要" in prompt


class TestModelRouter:
    """ModelRouter测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.router = ModelRouter()
    
    def test_route_reasoning(self):
        """测试推理任务路由"""
        model = self.router.route("derivation", "high")
        
        assert model['tier'] == 'high'
        assert 'DeepSeek-R1' in model['name']
    
    def test_route_code_generation(self):
        """测试代码生成路由"""
        model = self.router.route("code_generation", "medium")
        
        assert model['tier'] == 'medium'
    
    def test_route_formatting(self):
        """测试格式化路由"""
        model = self.router.route("formatting", "low")
        
        assert model['tier'] == 'low'
    
    def test_estimate_cost(self):
        """测试成本估算"""
        cost = self.router.estimate_cost("high", 1000)
        
        assert cost > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
