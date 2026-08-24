"""
pytest配置文件
"""

import pytest
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_configure(config):
    """pytest配置"""
    config.addinivalue_line("markers", "slow: 标记慢速测试")
    config.addinivalue_line("markers", "integration: 标记集成测试")


@pytest.fixture
def sample_dataframe():
    """示例DataFrame fixture"""
    import pandas as pd
    import numpy as np
    
    np.random.seed(42)
    return pd.DataFrame({
        'id': range(100),
        'value': np.random.randn(100),
        'category': np.random.choice(['A', 'B', 'C'], 100)
    })


@pytest.fixture
def temp_dir():
    """临时目录fixture"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
