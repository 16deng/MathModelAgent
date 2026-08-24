"""
数据画像模块

实现渐进式数据画像，将原始数据转换为轻量级摘要，降低Token消耗
"""

import json
import io
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DataProfile:
    """数据画像"""
    shape: tuple  # 数据形状
    columns: List[Dict[str, Any]]  # 列信息
    dtypes: Dict[str, str]  # 数据类型
    statistics: Dict[str, Any]  # 统计摘要
    missing_rates: Dict[str, float]  # 缺失率
    sample_data: List[Dict]  # 样例数据
    memory_usage: str  # 内存使用
    token_estimate: int  # 预估Token数
    
    def to_prompt(self, max_sample_rows: int = 5) -> str:
        """转换为Prompt文本"""
        lines = []
        lines.append(f"## 数据概览")
        lines.append(f"- 数据形状: {self.shape[0]} 行 × {self.shape[1]} 列")
        lines.append(f"- 内存占用: {self.memory_usage}")
        lines.append(f"- 预估Token: ~{self.token_estimate}")
        lines.append("")
        
        lines.append("## 列信息")
        lines.append("| 列名 | 类型 | 非空率 | 均值/示例 |")
        lines.append("|------|------|--------|-----------|")
        for col in self.columns[:20]:  # 最多显示20列
            name = col.get("name", "")
            dtype = col.get("dtype", "")
            non_null = f"{100 - self.missing_rates.get(name, 0):.1f}%"
            example = col.get("example", "")
            lines.append(f"| {name} | {dtype} | {non_null} | {example} |")
        
        lines.append("")
        lines.append("## 统计摘要")
        lines.append("```")
        lines.append(self._format_statistics())
        lines.append("```")
        
        lines.append("")
        lines.append("## 样例数据")
        lines.append("```")
        lines.append(self._format_sample(min(max_sample_rows, len(self.sample_data))))
        lines.append("```")
        
        return '\n'.join(lines)
    
    def _format_statistics(self) -> str:
        """格式化统计信息"""
        if not self.statistics:
            return "无统计信息"
        
        lines = []
        for col_name, stats in self.statistics.items():
            if isinstance(stats, dict):
                values = [f"{k}: {v}" for k, v in list(stats.items())[:5]]
                lines.append(f"{col_name}: {', '.join(values)}")
            else:
                lines.append(f"{col_name}: {stats}")
        
        return '\n'.join(lines[:20])  # 最多显示20行
    
    def _format_sample(self, rows: int) -> str:
        """格式化样例数据"""
        if not self.sample_data:
            return "无样例数据"
        
        # 简单格式化
        lines = []
        for i, row in enumerate(self.sample_data[:rows]):
            items = [f"{k}={v}" for k, v in list(row.items())[:8]]
            lines.append(f"行{i+1}: {', '.join(items)}")
        
        return '\n'.join(lines)


class DataProfiler:
    """数据画像器"""
    
    def __init__(self, max_sample_rows: int = 5, max_columns: int = 50):
        """
        初始化数据画像器
        
        Args:
            max_sample_rows: 最大样例行数
            max_columns: 最大列数
        """
        self.max_sample_rows = max_sample_rows
        self.max_columns = max_columns
    
    def profile_dataframe(self, df) -> DataProfile:
        """
        对DataFrame进行画像
        
        Args:
            df: pandas DataFrame
            
        Returns:
            数据画像
        """
        import pandas as pd
        import numpy as np
        
        # 基本信息
        shape = df.shape
        memory_bytes = df.memory_usage(deep=True).sum()
        memory_usage = self._format_memory(memory_bytes)
        
        # 列信息
        columns = []
        dtypes = {}
        missing_rates = {}
        statistics = {}
        
        for col in df.columns[:self.max_columns]:
            col_data = df[col]
            
            # 数据类型
            dtype = str(col_data.dtype)
            dtypes[col] = dtype
            
            # 缺失率
            missing_rate = col_data.isna().mean() * 100
            missing_rates[col] = round(missing_rate, 2)
            
            # 列信息
            col_info = {
                "name": col,
                "dtype": dtype,
                "non_null_count": int(col_data.notna().sum()),
                "example": self._get_example(col_data)
            }
            columns.append(col_info)
            
            # 统计信息
            if pd.api.types.is_numeric_dtype(col_data):
                stats = {
                    "mean": round(float(col_data.mean()), 4) if not col_data.isna().all() else None,
                    "std": round(float(col_data.std()), 4) if not col_data.isna().all() else None,
                    "min": float(col_data.min()) if not col_data.isna().all() else None,
                    "max": float(col_data.max()) if not col_data.isna().all() else None,
                    "median": float(col_data.median()) if not col_data.isna().all() else None,
                }
                statistics[col] = stats
            else:
                # 分类列
                value_counts = col_data.value_counts().head(5).to_dict()
                statistics[col] = {
                    "unique_count": int(col_data.nunique()),
                    "top_values": value_counts
                }
        
        # 样例数据
        sample_data = df.head(self.max_sample_rows).to_dict('records')
        
        # Token估算
        token_estimate = self._estimate_tokens(df)
        
        return DataProfile(
            shape=shape,
            columns=columns,
            dtypes=dtypes,
            statistics=statistics,
            missing_rates=missing_rates,
            sample_data=sample_data,
            memory_usage=memory_usage,
            token_estimate=token_estimate
        )
    
    def profile_csv(self, file_path: str) -> DataProfile:
        """
        对CSV文件进行画像
        
        Args:
            file_path: CSV文件路径
            
        Returns:
            数据画像
        """
        import pandas as pd
        
        # 读取CSV
        df = pd.read_csv(file_path)
        
        return self.profile_dataframe(df)
    
    def profile_json(self, data: Union[str, List, Dict]) -> DataProfile:
        """
        对JSON数据进行画像
        
        Args:
            data: JSON数据
            
        Returns:
            数据画像
        """
        import pandas as pd
        
        if isinstance(data, str):
            data = json.loads(data)
        
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            raise ValueError("不支持的数据格式")
        
        return self.profile_dataframe(df)
    
    def _get_example(self, series) -> str:
        """获取列的示例值"""
        import pandas as pd
        
        # 获取第一个非空值
        non_null = series.dropna()
        if len(non_null) == 0:
            return "N/A"
        
        value = non_null.iloc[0]
        
        # 格式化
        if isinstance(value, float):
            return f"{value:.4f}"
        elif isinstance(value, (int, str)):
            return str(value)[:30]
        else:
            return str(type(value).__name__)
    
    def _format_memory(self, bytes_count: int) -> str:
        """格式化内存大小"""
        if bytes_count < 1024:
            return f"{bytes_count} B"
        elif bytes_count < 1024 * 1024:
            return f"{bytes_count / 1024:.1f} KB"
        elif bytes_count < 1024 * 1024 * 1024:
            return f"{bytes_count / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_count / (1024 * 1024 * 1024):.1f} GB"
    
    def _estimate_tokens(self, df) -> int:
        """估算Token数"""
        # 简化估算：每个字符约0.5个token
        buffer = io.StringIO()
        df.info(buf=buffer)
        info_text = buffer.getvalue()
        
        # 统计摘要
        desc_text = df.describe().to_string()
        
        # 样例数据
        sample_text = df.head(3).to_string()
        
        total_chars = len(info_text) + len(desc_text) + len(sample_text)
        return int(total_chars * 0.5)


class ModelRouter:
    """模型分级路由器"""
    
    def __init__(self):
        """初始化路由器"""
        self.model_tiers = {
            "high": {
                "name": "DeepSeek-R1",
                "description": "高推理能力模型",
                "use_cases": ["推导", "评审", "复杂分析"],
                "cost_per_1k_tokens": 0.02
            },
            "medium": {
                "name": "DeepSeek-V3",
                "description": "平衡模型",
                "use_cases": ["代码生成", "一般分析"],
                "cost_per_1k_tokens": 0.01
            },
            "low": {
                "name": "GPT-4o-mini",
                "description": "轻量高性价比模型",
                "use_cases": ["代码修改", "格式化", "简单任务"],
                "cost_per_1k_tokens": 0.002
            }
        }
    
    def route(self, task_type: str, complexity: str = "medium") -> Dict[str, Any]:
        """
        根据任务类型和复杂度路由模型
        
        Args:
            task_type: 任务类型
            complexity: 复杂度 (low, medium, high)
            
        Returns:
            模型配置
        """
        # 任务类型到模型层级的映射
        task_tier_map = {
            "derivation": "high",  # 推导
            "review": "high",  # 评审
            "analysis": "high",  # 复杂分析
            "code_generation": "medium",  # 代码生成
            "general": "medium",  # 一般任务
            "code_edit": "low",  # 代码修改
            "formatting": "low",  # 格式化
            "simple": "low",  # 简单任务
        }
        
        # 根据复杂度调整
        if complexity == "high":
            tier = "high"
        elif complexity == "low":
            tier = "low"
        else:
            tier = task_tier_map.get(task_type, "medium")
        
        return {
            "tier": tier,
            **self.model_tiers[tier]
        }
    
    def estimate_cost(self, tier: str, token_count: int) -> float:
        """估算成本"""
        model = self.model_tiers.get(tier, self.model_tiers["medium"])
        return (token_count / 1000) * model["cost_per_1k_tokens"]


# ============== 测试代码 ==============

if __name__ == "__main__":
    print("=" * 60)
    print("测试 数据画像与模型路由")
    print("=" * 60)
    
    # 创建测试数据
    import pandas as pd
    import numpy as np
    
    np.random.seed(42)
    df = pd.DataFrame({
        'id': range(1000),
        'name': [f'item_{i}' for i in range(1000)],
        'value': np.random.randn(1000),
        'category': np.random.choice(['A', 'B', 'C'], 1000),
        'date': pd.date_range('2024-01-01', periods=1000, freq='D')
    })
    
    # 添加一些缺失值
    df.loc[df.sample(frac=0.1).index, 'value'] = np.nan
    
    print(f"\n原始数据形状: {df.shape}")
    print(f"原始数据内存: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")
    
    # 测试数据画像
    profiler = DataProfiler()
    profile = profiler.profile_dataframe(df)
    
    print(f"\n--- 数据画像 ---")
    print(f"形状: {profile.shape}")
    print(f"列数: {len(profile.columns)}")
    print(f"内存占用: {profile.memory_usage}")
    print(f"预估Token: {profile.token_estimate}")
    
    print(f"\n--- Prompt输出 ---")
    prompt = profile.to_prompt(max_sample_rows=3)
    print(prompt[:1000])
    
    # 测试Token对比
    print(f"\n--- Token对比 ---")
    original_tokens = len(df.to_string()) * 0.5
    profile_tokens = profile.token_estimate
    reduction = (1 - profile_tokens / original_tokens) * 100
    print(f"原始数据Token估算: {original_tokens:.0f}")
    print(f"画像后Token估算: {profile_tokens}")
    print(f"Token减少: {reduction:.1f}%")
    
    # 测试模型路由
    print(f"\n--- 模型路由 ---")
    router = ModelRouter()
    
    tasks = [
        ("derivation", "high"),
        ("code_generation", "medium"),
        ("formatting", "low"),
    ]
    
    for task_type, complexity in tasks:
        model = router.route(task_type, complexity)
        cost = router.estimate_cost(model["tier"], 1000)
        print(f"{task_type} ({complexity}): {model['name']} (${cost:.4f}/1k tokens)")
    
    print("\n" + "=" * 60)
    print("数据画像与模型路由测试完成！")
    print("=" * 60)
