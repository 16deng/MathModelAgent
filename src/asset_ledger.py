"""
数据资产账本模块

实现抗幻觉防线：动态资产账本 + Typst语义化占位符
"""

import json
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime


@dataclass
class AssetRecord:
    """资产记录"""
    key: str
    value: Any
    asset_type: str  # scalar, figure, table, text
    source: str  # 来源
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class AssetLedger:
    """数据资产账本"""
    
    def __init__(self, ledger_path: str = "./artifacts.json"):
        """
        初始化资产账本
        
        Args:
            ledger_path: 账本文件路径
        """
        self.ledger_path = Path(ledger_path)
        self.assets: Dict[str, AssetRecord] = {}
        self._load_ledger()
    
    def _load_ledger(self):
        """加载账本"""
        if self.ledger_path.exists():
            try:
                with open(self.ledger_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, record in data.items():
                        self.assets[key] = AssetRecord(**record)
            except Exception as e:
                print(f"加载账本失败: {e}")
    
    def _save_ledger(self):
        """保存账本"""
        data = {key: asdict(record) for key, record in self.assets.items()}
        with open(self.ledger_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_scalar(self, key: str, value: float, source: str = "", 
                   metadata: Optional[Dict] = None) -> AssetRecord:
        """
        添加标量指标
        
        Args:
            key: 资产键
            value: 标量值
            source: 来源
            metadata: 元数据
            
        Returns:
            资产记录
        """
        record = AssetRecord(
            key=key,
            value=value,
            asset_type="scalar",
            source=source,
            metadata=metadata or {}
        )
        self.assets[key] = record
        self._save_ledger()
        return record
    
    def add_figure(self, key: str, path: str, source: str = "",
                   metadata: Optional[Dict] = None) -> AssetRecord:
        """
        添加图表
        
        Args:
            key: 资产键
            path: 图表文件路径
            source: 来源
            metadata: 元数据
            
        Returns:
            资产记录
        """
        record = AssetRecord(
            key=key,
            value=path,
            asset_type="figure",
            source=source,
            metadata=metadata or {}
        )
        self.assets[key] = record
        self._save_ledger()
        return record
    
    def add_table(self, key: str, data: List[Dict], source: str = "",
                  metadata: Optional[Dict] = None) -> AssetRecord:
        """
        添加表格数据
        
        Args:
            key: 资产键
            data: 表格数据
            source: 来源
            metadata: 元数据
            
        Returns:
            资产记录
        """
        record = AssetRecord(
            key=key,
            value=data,
            asset_type="table",
            source=source,
            metadata=metadata or {}
        )
        self.assets[key] = record
        self._save_ledger()
        return record
    
    def add_text(self, key: str, text: str, source: str = "",
                 metadata: Optional[Dict] = None) -> AssetRecord:
        """
        添加文本
        
        Args:
            key: 资产键
            text: 文本内容
            source: 来源
            metadata: 元数据
            
        Returns:
            资产记录
        """
        record = AssetRecord(
            key=key,
            value=text,
            asset_type="text",
            source=source,
            metadata=metadata or {}
        )
        self.assets[key] = record
        self._save_ledger()
        return record
    
    def get(self, key: str) -> Optional[AssetRecord]:
        """获取资产记录"""
        return self.assets.get(key)
    
    def get_value(self, key: str) -> Any:
        """获取资产值"""
        record = self.assets.get(key)
        return record.value if record else None
    
    def get_all(self) -> Dict[str, AssetRecord]:
        """获取所有资产"""
        return self.assets.copy()
    
    def get_by_type(self, asset_type: str) -> Dict[str, AssetRecord]:
        """按类型获取资产"""
        return {
            key: record for key, record in self.assets.items()
            if record.asset_type == asset_type
        }
    
    def search(self, keyword: str) -> Dict[str, AssetRecord]:
        """搜索资产"""
        results = {}
        for key, record in self.assets.items():
            if keyword.lower() in key.lower() or keyword.lower() in str(record.value).lower():
                results[key] = record
        return results
    
    def delete(self, key: str) -> bool:
        """删除资产"""
        if key in self.assets:
            del self.assets[key]
            self._save_ledger()
            return True
        return False
    
    def clear(self):
        """清空账本"""
        self.assets.clear()
        self._save_ledger()
    
    def summary(self) -> Dict[str, Any]:
        """获取摘要"""
        type_counts = {}
        for record in self.assets.values():
            type_counts[record.asset_type] = type_counts.get(record.asset_type, 0) + 1
        
        return {
            "total_assets": len(self.assets),
            "type_counts": type_counts,
            "keys": list(self.assets.keys())
        }
    
    def to_typst_macros(self) -> str:
        """
        生成Typst宏定义
        
        用于在Typst模板中引用资产值
        """
        lines = []
        lines.append("// 自动生成的资产宏定义")
        lines.append("// 请勿手动修改")
        lines.append("")
        
        for key, record in self.assets.items():
            safe_key = key.replace("-", "_").replace(" ", "_")
            
            if record.asset_type == "scalar":
                # 标量宏
                value = record.value
                if isinstance(value, float):
                    lines.append(f'#let {safe_key} = "{value:.4f}"')
                else:
                    lines.append(f'#let {safe_key} = "{value}"')
            
            elif record.asset_type == "figure":
                # 图表宏
                path = record.value.replace("\\", "/")
                lines.append(f'#let {safe_key}_path = "{path}"')
                lines.append(f'#let {safe_key}() = figure(image({safe_key}_path))')
            
            elif record.asset_type == "table":
                # 表格宏
                lines.append(f'#let {safe_key}_data = {json.dumps(record.value)}')
        
        return '\n'.join(lines)
    
    def inject_typst(self, typst_template: str) -> str:
        """
        将资产值注入Typst模板
        
        Args:
            typst_template: Typst模板内容
            
        Returns:
            注入后的Typst内容
        """
        import re
        
        result = typst_template
        
        # 替换 #metric("key") 格式
        def replace_metric(match):
            key = match.group(1)
            record = self.assets.get(key)
            if record and record.asset_type == "scalar":
                value = record.value
                if isinstance(value, float):
                    return f"{value:.4f}"
                return str(value)
            return match.group(0)
        
        result = re.sub(r'#metric\("(\w+)"\)', replace_metric, result)
        
        # 替换 #fig("key") 格式
        def replace_fig(match):
            key = match.group(1)
            record = self.assets.get(key)
            if record and record.asset_type == "figure":
                path = record.value.replace("\\", "/")
                return f'figure(image("{path}"))'
            return match.group(0)
        
        result = re.sub(r'#fig\("(\w+)"\)', replace_fig, result)
        
        return result


class TypstTemplateEngine:
    """Typst模板引擎"""
    
    def __init__(self, template_dir: str = "./templates"):
        """
        初始化模板引擎
        
        Args:
            template_dir: 模板目录
        """
        self.template_dir = Path(template_dir)
        self.ledger = AssetLedger()
    
    def render(self, template_name: str, context: Dict[str, Any] = None) -> str:
        """
        渲染模板
        
        Args:
            template_name: 模板名称
            context: 上下文数据
            
        Returns:
            渲染后的Typst内容
        """
        template_path = self.template_dir / f"{template_name}.typ"
        
        if not template_path.exists():
            raise FileNotFoundError(f"模板不存在: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 注入上下文变量
        if context:
            for key, value in context.items():
                placeholder = f"{{{{ {key} }}}}"
                template_content = template_content.replace(placeholder, str(value))
        
        # 注入资产值
        result = self.ledger.inject_typst(template_content)
        
        return result


# ============== 测试代码 ==============

if __name__ == "__main__":
    print("=" * 60)
    print("测试 资产账本与Typst注入")
    print("=" * 60)
    
    # 创建资产账本
    ledger = AssetLedger("./test_artifacts.json")
    
    # 添加标量指标
    print("\n--- 添加标量指标 ---")
    ledger.add_scalar("train_loss", 0.0234, source="training_script")
    ledger.add_scalar("val_loss", 0.0312, source="training_script")
    ledger.add_scalar("R2", 0.9567, source="evaluation_script")
    ledger.add_scalar("RMSE", 0.0456, source="evaluation_script")
    
    # 添加图表
    print("\n--- 添加图表 ---")
    ledger.add_figure("convergence_curve", "./outputs/convergence.png", source="plot_script")
    ledger.add_figure("residual_plot", "./outputs/residuals.png", source="plot_script")
    
    # 添加表格
    print("\n--- 添加表格 ---")
    ledger.add_table("comparison", [
        {"model": "Linear", "R2": 0.85, "RMSE": 0.08},
        {"model": "Polynomial", "R2": 0.92, "RMSE": 0.06},
        {"model": "Neural", "R2": 0.96, "RMSE": 0.04},
    ], source="evaluation_script")
    
    # 获取摘要
    print("\n--- 资产摘要 ---")
    summary = ledger.summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    # 获取特定资产
    print("\n--- 获取资产 ---")
    r2_record = ledger.get("R2")
    print(f"R²值: {r2_record.value}")
    print(f"来源: {r2_record.source}")
    print(f"时间: {r2_record.timestamp}")
    
    # 生成Typst宏
    print("\n--- Typst宏定义 ---")
    macros = ledger.to_typst_macros()
    print(macros)
    
    # 测试Typst注入
    print("\n--- Typst注入测试 ---")
    typst_template = """
= 模型评估结果

模型的R²值为 #metric("R2")，RMSE为 #metric("RMSE")。

训练损失: #metric("train_loss")
验证损失: #metric("val_loss")

收敛曲线: #fig("convergence_curve")
"""
    
    injected = ledger.inject_typst(typst_template)
    print(injected)
    
    # 清理测试文件
    import os
    if os.path.exists("./test_artifacts.json"):
        os.remove("./test_artifacts.json")
    
    print("\n" + "=" * 60)
    print("资产账本与Typst注入测试完成！")
    print("=" * 60)
