"""
数模评测基准模块

实现MathModel-Bench评测基准和全链路可观测性
"""

import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime


@dataclass
class BenchmarkTask:
    """评测任务"""
    task_id: str
    name: str
    category: str  # optimization, differential, timeseries, etc.
    difficulty: str  # easy, medium, hard
    description: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    evaluation_criteria: Dict[str, Any]
    source: str = ""  # 来源（国赛/美赛年份）


@dataclass
class BenchmarkResult:
    """评测结果"""
    task_id: str
    model_name: str
    pass_at_1: bool  # 单次执行是否成功
    execution_success: bool
    token_consumption: int
    execution_time: float
    numeric_consistency: bool  # 数值一致性
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


class MathModelBench:
    """数模评测基准"""
    
    def __init__(self, bench_dir: str = "./benchmark"):
        """
        初始化评测基准
        
        Args:
            bench_dir: 评测数据目录
        """
        self.bench_dir = Path(bench_dir)
        self.bench_dir.mkdir(parents=True, exist_ok=True)
        
        self.tasks: Dict[str, BenchmarkTask] = {}
        self.results: List[BenchmarkResult] = []
        
        # 加载内置任务
        self._load_builtin_tasks()
    
    def _load_builtin_tasks(self):
        """加载内置评测任务"""
        builtin_tasks = [
            BenchmarkTask(
                task_id="opt_001",
                name="线性规划问题",
                category="optimization",
                difficulty="easy",
                description="某工厂生产两种产品，求利润最大化的生产方案",
                input_data={
                    "objective": [3, 5],
                    "constraints": [[2, 4], [1, 2]],
                    "bounds": [12, 8]
                },
                expected_output={
                    "optimal_value": 15.0,
                    "solution": [0, 3]
                },
                evaluation_criteria={
                    "pass_threshold": 0.01,
                    "check_constraints": True
                },
                source="国赛2023"
            ),
            BenchmarkTask(
                task_id="opt_002",
                name="整数规划问题",
                category="optimization",
                difficulty="medium",
                description="背包问题：选择物品使总价值最大",
                input_data={
                    "weights": [2, 3, 4, 5],
                    "values": [3, 4, 5, 6],
                    "capacity": 8
                },
                expected_output={
                    "max_value": 10,
                    "selected_items": [1, 2]
                },
                evaluation_criteria={
                    "pass_threshold": 0,
                    "check_feasibility": True
                },
                source="国赛2022"
            ),
            BenchmarkTask(
                task_id="diff_001",
                name="微分方程求解",
                category="differential",
                difficulty="medium",
                description="求解一阶常微分方程",
                input_data={
                    "equation": "dy/dx = -2*y + 1",
                    "initial_condition": {"x": 0, "y": 0},
                    "target_x": 1.0
                },
                expected_output={
                    "target_y": 0.4323
                },
                evaluation_criteria={
                    "pass_threshold": 0.01,
                    "method": "numerical"
                },
                source="美赛2023"
            ),
            BenchmarkTask(
                task_id="ts_001",
                name="时间序列预测",
                category="timeseries",
                difficulty="medium",
                description="预测未来7天的销售额",
                input_data={
                    "historical_data": [100, 120, 115, 130, 125, 140, 135],
                    "forecast_horizon": 7
                },
                expected_output={
                    "trend": "increasing",
                    "range": [130, 160]
                },
                evaluation_criteria={
                    "check_trend": True,
                    "range_tolerance": 0.2
                },
                source="国赛2021"
            ),
            BenchmarkTask(
                task_id="eval_001",
                name="模型评估指标",
                category="evaluation",
                difficulty="easy",
                description="计算回归模型的评估指标",
                input_data={
                    "y_true": [1, 2, 3, 4, 5],
                    "y_pred": [1.1, 2.2, 2.8, 4.1, 5.2]
                },
                expected_output={
                    "R2_range": [0.95, 1.0],
                    "RMSE_max": 0.3
                },
                evaluation_criteria={
                    "check_R2": True,
                    "check_RMSE": True
                },
                source="通用"
            ),
        ]
        
        for task in builtin_tasks:
            self.tasks[task.task_id] = task
    
    def get_task(self, task_id: str) -> Optional[BenchmarkTask]:
        """获取评测任务"""
        return self.tasks.get(task_id)
    
    def get_tasks_by_category(self, category: str) -> List[BenchmarkTask]:
        """按类别获取任务"""
        return [t for t in self.tasks.values() if t.category == category]
    
    def get_tasks_by_difficulty(self, difficulty: str) -> List[BenchmarkTask]:
        """按难度获取任务"""
        return [t for t in self.tasks.values() if t.difficulty == difficulty]
    
    def add_result(self, result: BenchmarkResult):
        """添加评测结果"""
        if not result.timestamp:
            result.timestamp = datetime.now().isoformat()
        self.results.append(result)
    
    def evaluate_result(self, task_id: str, actual_output: Dict[str, Any],
                        execution_success: bool, token_consumption: int,
                        execution_time: float) -> BenchmarkResult:
        """
        评测结果
        
        Args:
            task_id: 任务ID
            actual_output: 实际输出
            execution_success: 执行是否成功
            token_consumption: Token消耗
            execution_time: 执行时间
            
        Returns:
            评测结果
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        # 检查是否通过
        pass_at_1 = False
        numeric_consistency = True
        details = {}
        
        if execution_success:
            # 检查数值一致性
            for key, expected in task.expected_output.items():
                if key in actual_output:
                    actual = actual_output[key]
                    
                    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                        threshold = task.evaluation_criteria.get("pass_threshold", 0.01)
                        if abs(actual - expected) > threshold * abs(expected):
                            numeric_consistency = False
                            details[f"{key}_mismatch"] = {
                                "expected": expected,
                                "actual": actual,
                                "diff": abs(actual - expected)
                            }
                    
                    elif isinstance(expected, list) and isinstance(actual, list):
                        if sorted(expected) != sorted(actual):
                            numeric_consistency = False
                            details[f"{key}_mismatch"] = {
                                "expected": expected,
                                "actual": actual
                            }
            
            pass_at_1 = numeric_consistency
        
        result = BenchmarkResult(
            task_id=task_id,
            model_name="MathModelAgent",
            pass_at_1=pass_at_1,
            execution_success=execution_success,
            token_consumption=token_consumption,
            execution_time=execution_time,
            numeric_consistency=numeric_consistency,
            details=details
        )
        
        self.add_result(result)
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取评测统计"""
        if not self.results:
            return {"total": 0}
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.pass_at_1)
        execution_success = sum(1 for r in self.results if r.execution_success)
        numeric_consistent = sum(1 for r in self.results if r.numeric_consistency)
        
        avg_tokens = sum(r.token_consumption for r in self.results) / total
        avg_time = sum(r.execution_time for r in self.results) / total
        
        return {
            "total_tasks": total,
            "passed": passed,
            "pass_at_1_rate": passed / total,
            "execution_success_rate": execution_success / total,
            "numeric_consistency_rate": numeric_consistent / total,
            "avg_token_consumption": avg_tokens,
            "avg_execution_time": avg_time
        }
    
    def print_report(self):
        """打印评测报告"""
        stats = self.get_statistics()
        
        print("=" * 60)
        print("MathModel-Bench 评测报告")
        print("=" * 60)
        
        print(f"\n总任务数: {stats.get('total_tasks', 0)}")
        print(f"通过任务: {stats.get('passed', 0)}")
        print(f"Pass@1: {stats.get('pass_at_1_rate', 0):.1%}")
        print(f"执行成功率: {stats.get('execution_success_rate', 0):.1%}")
        print(f"数值一致性: {stats.get('numeric_consistency_rate', 0):.1%}")
        print(f"平均Token消耗: {stats.get('avg_token_consumption', 0):.0f}")
        print(f"平均执行时间: {stats.get('avg_execution_time', 0):.2f}秒")
        
        print("\n--- 详细结果 ---")
        for result in self.results:
            status = "✓" if result.pass_at_1 else "✗"
            print(f"{status} [{result.task_id}] "
                  f"Pass@1={result.pass_at_1}, "
                  f"Tokens={result.token_consumption}, "
                  f"Time={result.execution_time:.2f}s")
        
        print("=" * 60)


class TraceCollector:
    """全链路追踪收集器"""
    
    def __init__(self):
        """初始化追踪收集器"""
        self.traces: List[Dict[str, Any]] = []
        self.current_trace: Optional[Dict[str, Any]] = None
    
    def start_trace(self, trace_id: str, metadata: Dict[str, Any] = None):
        """开始追踪"""
        self.current_trace = {
            "trace_id": trace_id,
            "start_time": time.time(),
            "metadata": metadata or {},
            "spans": []
        }
    
    def add_span(self, span_name: str, span_type: str, 
                 metadata: Dict[str, Any] = None):
        """添加跨度"""
        if not self.current_trace:
            return
        
        span = {
            "name": span_name,
            "type": span_type,
            "start_time": time.time(),
            "metadata": metadata or {}
        }
        self.current_trace["spans"].append(span)
    
    def end_span(self, span_name: str, status: str = "success",
                 output: Any = None):
        """结束跨度"""
        if not self.current_trace:
            return
        
        for span in reversed(self.current_trace["spans"]):
            if span["name"] == span_name and "end_time" not in span:
                span["end_time"] = time.time()
                span["duration"] = span["end_time"] - span["start_time"]
                span["status"] = status
                span["output"] = output
                break
    
    def end_trace(self, status: str = "success"):
        """结束追踪"""
        if not self.current_trace:
            return
        
        self.current_trace["end_time"] = time.time()
        self.current_trace["duration"] = (
            self.current_trace["end_time"] - self.current_trace["start_time"]
        )
        self.current_trace["status"] = status
        
        self.traces.append(self.current_trace)
        self.current_trace = None
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取追踪统计"""
        if not self.traces:
            return {"total_traces": 0}
        
        total = len(self.traces)
        avg_duration = sum(t["duration"] for t in self.traces) / total
        
        # 统计各类型跨度
        span_types = {}
        for trace in self.traces:
            for span in trace.get("spans", []):
                span_type = span["type"]
                if span_type not in span_types:
                    span_types[span_type] = {"count": 0, "total_duration": 0}
                span_types[span_type]["count"] += 1
                span_types[span_type]["total_duration"] += span.get("duration", 0)
        
        # 计算平均值
        for span_type in span_types:
            count = span_types[span_type]["count"]
            span_types[span_type]["avg_duration"] = (
                span_types[span_type]["total_duration"] / count
            )
        
        return {
            "total_traces": total,
            "avg_duration": avg_duration,
            "span_types": span_types
        }
    
    def export_traces(self, output_path: str):
        """导出追踪数据"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.traces, f, ensure_ascii=False, indent=2, default=str)


# ============== 测试代码 ==============

if __name__ == "__main__":
    print("=" * 60)
    print("测试 评测基准与追踪")
    print("=" * 60)
    
    # 测试评测基准
    bench = MathModelBench()
    
    print(f"\n内置任务数: {len(bench.tasks)}")
    
    # 模拟评测
    print("\n--- 模拟评测 ---")
    
    # 任务1: 线性规划（成功）
    result1 = bench.evaluate_result(
        "opt_001",
        {"optimal_value": 15.0, "solution": [0, 3]},
        execution_success=True,
        token_consumption=500,
        execution_time=1.2
    )
    print(f"opt_001: Pass@1={result1.pass_at_1}")
    
    # 任务2: 微分方程（部分成功）
    result2 = bench.evaluate_result(
        "diff_001",
        {"target_y": 0.4350},  # 接近但不完全一致
        execution_success=True,
        token_consumption=800,
        execution_time=2.5
    )
    print(f"diff_001: Pass@1={result2.pass_at_1}")
    
    # 任务3: 执行失败
    result3 = bench.evaluate_result(
        "opt_002",
        {},
        execution_success=False,
        token_consumption=300,
        execution_time=0.5
    )
    print(f"opt_002: Pass@1={result3.pass_at_1}")
    
    # 打印报告
    bench.print_report()
    
    # 测试追踪
    print("\n--- 测试追踪 ---")
    collector = TraceCollector()
    
    collector.start_trace("trace_001", {"task": "opt_001"})
    
    collector.add_span("problem_analysis", "llm_call", {"model": "gpt-4"})
    time.sleep(0.1)
    collector.end_span("problem_analysis", "success")
    
    collector.add_span("code_generation", "llm_call", {"model": "gpt-4"})
    time.sleep(0.1)
    collector.end_span("code_generation", "success")
    
    collector.add_span("code_execution", "tool_call")
    time.sleep(0.05)
    collector.end_span("code_execution", "success")
    
    collector.end_trace("success")
    
    stats = collector.get_statistics()
    print(f"总追踪数: {stats['total_traces']}")
    print(f"平均耗时: {stats['avg_duration']:.3f}秒")
    
    print("\n" + "=" * 60)
    print("评测基准与追踪测试完成！")
    print("=" * 60)
