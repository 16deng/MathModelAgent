"""
评估器模块

提供Agent任务处理指标的评估功能
"""

import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class TaskMetrics:
    """任务指标"""
    task_id: str
    task_type: str
    start_time: str
    end_time: Optional[str] = None
    duration: Optional[float] = None  # 秒
    success: bool = False
    retry_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeExecutionMetrics:
    """代码执行指标"""
    execution_id: str
    task_id: str
    code_length: int
    execution_time: float  # 秒
    success: bool
    has_figure: bool = False
    output_length: int = 0
    error_message: Optional[str] = None
    auto_fixed: bool = False
    fix_attempts: int = 0


@dataclass
class RAGMetrics:
    """RAG检索指标"""
    query_id: str
    task_id: str
    query_text: str
    retrieval_time: float  # 秒
    result_count: int
    relevant_count: int
    precision: float = 0.0  # 准确率
    recall: float = 0.0  # 召回率
    top_k: int = 3


@dataclass
class UserExperienceMetrics:
    """用户体验指标"""
    session_id: str
    task_id: str
    response_time: float  # 秒
    interaction_count: int  # 人机交互次数
    user_satisfaction: Optional[int] = None  # 1-5分
    feedback: Optional[str] = None


@dataclass
class ResourceMetrics:
    """资源消耗指标"""
    session_id: str
    task_id: str
    token_consumption: int
    api_calls: int
    memory_usage: Optional[float] = None  # MB
    cost_estimate: Optional[float] = None  # 美元


class AgentEvaluator:
    """Agent评估器"""
    
    def __init__(self, output_dir: str = "./evaluation"):
        """
        初始化评估器
        
        Args:
            output_dir: 评估结果输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.task_metrics: List[TaskMetrics] = []
        self.code_metrics: List[CodeExecutionMetrics] = []
        self.rag_metrics: List[RAGMetrics] = []
        self.ux_metrics: List[UserExperienceMetrics] = []
        self.resource_metrics: List[ResourceMetrics] = []
        
        self.current_task_id: Optional[str] = None
        self.task_start_time: Optional[float] = None
    
    def start_task(self, task_id: str, task_type: str) -> str:
        """
        开始任务评估
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            
        Returns:
            任务ID
        """
        self.current_task_id = task_id
        self.task_start_time = time.time()
        
        metrics = TaskMetrics(
            task_id=task_id,
            task_type=task_type,
            start_time=datetime.now().isoformat()
        )
        self.task_metrics.append(metrics)
        
        return task_id
    
    def end_task(self, task_id: str, success: bool, 
                 error_message: Optional[str] = None, **kwargs):
        """
        结束任务评估
        
        Args:
            task_id: 任务ID
            success: 是否成功
            error_message: 错误信息
            **kwargs: 其他元数据
        """
        for metrics in self.task_metrics:
            if metrics.task_id == task_id:
                metrics.end_time = datetime.now().isoformat()
                metrics.duration = time.time() - self.task_start_time if self.task_start_time else 0
                metrics.success = success
                metrics.error_message = error_message
                metrics.metadata.update(kwargs)
                break
        
        if self.current_task_id == task_id:
            self.current_task_id = None
            self.task_start_time = None
    
    def record_code_execution(self, task_id: str, code: str, 
                              execution_time: float, success: bool,
                              has_figure: bool = False, output_length: int = 0,
                              error_message: Optional[str] = None,
                              auto_fixed: bool = False, fix_attempts: int = 0):
        """
        记录代码执行指标
        
        Args:
            task_id: 任务ID
            code: 代码内容
            execution_time: 执行时间
            success: 是否成功
            has_figure: 是否有图表
            output_length: 输出长度
            error_message: 错误信息
            auto_fixed: 是否自动修复
            fix_attempts: 修复尝试次数
        """
        metrics = CodeExecutionMetrics(
            execution_id=f"exec-{len(self.code_metrics)}",
            task_id=task_id,
            code_length=len(code),
            execution_time=execution_time,
            success=success,
            has_figure=has_figure,
            output_length=output_length,
            error_message=error_message,
            auto_fixed=auto_fixed,
            fix_attempts=fix_attempts
        )
        self.code_metrics.append(metrics)
    
    def record_rag_retrieval(self, task_id: str, query: str,
                             retrieval_time: float, results: List[Dict],
                             relevant_ids: Optional[List[str]] = None,
                             top_k: int = 3):
        """
        记录RAG检索指标
        
        Args:
            task_id: 任务ID
            query: 查询文本
            retrieval_time: 检索时间
            results: 检索结果
            relevant_ids: 相关文档ID列表
            top_k: 返回结果数
        """
        result_count = len(results)
        relevant_count = 0
        
        if relevant_ids:
            result_ids = [r.get('id', '') for r in results]
            relevant_count = len(set(result_ids) & set(relevant_ids))
        
        precision = relevant_count / result_count if result_count > 0 else 0
        recall = relevant_count / len(relevant_ids) if relevant_ids else 0
        
        metrics = RAGMetrics(
            query_id=f"rag-{len(self.rag_metrics)}",
            task_id=task_id,
            query_text=query,
            retrieval_time=retrieval_time,
            result_count=result_count,
            relevant_count=relevant_count,
            precision=precision,
            recall=recall,
            top_k=top_k
        )
        self.rag_metrics.append(metrics)
    
    def record_user_experience(self, session_id: str, task_id: str,
                               response_time: float, interaction_count: int,
                               user_satisfaction: Optional[int] = None,
                               feedback: Optional[str] = None):
        """
        记录用户体验指标
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            response_time: 响应时间
            interaction_count: 交互次数
            user_satisfaction: 用户满意度
            feedback: 用户反馈
        """
        metrics = UserExperienceMetrics(
            session_id=session_id,
            task_id=task_id,
            response_time=response_time,
            interaction_count=interaction_count,
            user_satisfaction=user_satisfaction,
            feedback=feedback
        )
        self.ux_metrics.append(metrics)
    
    def record_resource_usage(self, session_id: str, task_id: str,
                              token_consumption: int, api_calls: int,
                              memory_usage: Optional[float] = None,
                              cost_estimate: Optional[float] = None):
        """
        记录资源消耗指标
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            token_consumption: Token消耗
            api_calls: API调用次数
            memory_usage: 内存使用
            cost_estimate: 成本估算
        """
        metrics = ResourceMetrics(
            session_id=session_id,
            task_id=task_id,
            token_consumption=token_consumption,
            api_calls=api_calls,
            memory_usage=memory_usage,
            cost_estimate=cost_estimate
        )
        self.resource_metrics.append(metrics)
    
    def get_task_summary(self) -> Dict[str, Any]:
        """获取任务指标摘要"""
        if not self.task_metrics:
            return {}
        
        total_tasks = len(self.task_metrics)
        successful_tasks = sum(1 for m in self.task_metrics if m.success)
        total_duration = sum(m.duration or 0 for m in self.task_metrics)
        total_retries = sum(m.retry_count for m in self.task_metrics)
        
        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
            "average_duration": total_duration / total_tasks if total_tasks > 0 else 0,
            "total_retries": total_retries,
            "average_retries": total_retries / total_tasks if total_tasks > 0 else 0
        }
    
    def get_code_execution_summary(self) -> Dict[str, Any]:
        """获取代码执行指标摘要"""
        if not self.code_metrics:
            return {}
        
        total_executions = len(self.code_metrics)
        successful_executions = sum(1 for m in self.code_metrics if m.success)
        auto_fixed = sum(1 for m in self.code_metrics if m.auto_fixed)
        total_time = sum(m.execution_time for m in self.code_metrics)
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "auto_fixed_count": auto_fixed,
            "auto_fix_rate": auto_fixed / total_executions if total_executions > 0 else 0,
            "average_execution_time": total_time / total_executions if total_executions > 0 else 0
        }
    
    def get_rag_summary(self) -> Dict[str, Any]:
        """获取RAG检索指标摘要"""
        if not self.rag_metrics:
            return {}
        
        total_queries = len(self.rag_metrics)
        total_time = sum(m.retrieval_time for m in self.rag_metrics)
        avg_precision = sum(m.precision for m in self.rag_metrics) / total_queries
        avg_recall = sum(m.recall for m in self.rag_metrics) / total_queries
        
        return {
            "total_queries": total_queries,
            "average_retrieval_time": total_time / total_queries if total_queries > 0 else 0,
            "average_precision": avg_precision,
            "average_recall": avg_recall,
            "f1_score": 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0
        }
    
    def get_ux_summary(self) -> Dict[str, Any]:
        """获取用户体验指标摘要"""
        if not self.ux_metrics:
            return {}
        
        total_interactions = sum(m.interaction_count for m in self.ux_metrics)
        avg_response_time = sum(m.response_time for m in self.ux_metrics) / len(self.ux_metrics)
        satisfaction_scores = [m.user_satisfaction for m in self.ux_metrics if m.user_satisfaction]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
        
        return {
            "total_sessions": len(self.ux_metrics),
            "total_interactions": total_interactions,
            "average_interactions": total_interactions / len(self.ux_metrics) if self.ux_metrics else 0,
            "average_response_time": avg_response_time,
            "average_satisfaction": avg_satisfaction
        }
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """获取资源消耗指标摘要"""
        if not self.resource_metrics:
            return {}
        
        total_tokens = sum(m.token_consumption for m in self.resource_metrics)
        total_api_calls = sum(m.api_calls for m in self.resource_metrics)
        total_cost = sum(m.cost_estimate or 0 for m in self.resource_metrics)
        
        return {
            "total_tokens": total_tokens,
            "total_api_calls": total_api_calls,
            "average_tokens_per_task": total_tokens / len(self.resource_metrics) if self.resource_metrics else 0,
            "average_api_calls_per_task": total_api_calls / len(self.resource_metrics) if self.resource_metrics else 0,
            "total_cost": total_cost,
            "average_cost_per_task": total_cost / len(self.resource_metrics) if self.resource_metrics else 0
        }
    
    def get_full_report(self) -> Dict[str, Any]:
        """获取完整评估报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "task_summary": self.get_task_summary(),
            "code_execution_summary": self.get_code_execution_summary(),
            "rag_summary": self.get_rag_summary(),
            "ux_summary": self.get_ux_summary(),
            "resource_summary": self.get_resource_summary()
        }
    
    def save_report(self, filename: Optional[str] = None):
        """
        保存评估报告
        
        Args:
            filename: 文件名
        """
        if filename is None:
            filename = f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.output_dir / filename
        report = self.get_full_report()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"评估报告已保存: {filepath}")
        return filepath
    
    def print_summary(self):
        """打印评估摘要"""
        report = self.get_full_report()
        
        print("=" * 60)
        print("Agent任务处理指标评估报告")
        print("=" * 60)
        
        print("\n1. 任务完成指标:")
        task_summary = report.get("task_summary", {})
        print(f"   - 总任务数: {task_summary.get('total_tasks', 0)}")
        print(f"   - 成功任务数: {task_summary.get('successful_tasks', 0)}")
        print(f"   - 任务成功率: {task_summary.get('success_rate', 0):.2%}")
        print(f"   - 平均耗时: {task_summary.get('average_duration', 0):.2f}秒")
        print(f"   - 平均重试次数: {task_summary.get('average_retries', 0):.2f}")
        
        print("\n2. 代码执行指标:")
        code_summary = report.get("code_execution_summary", {})
        print(f"   - 总执行次数: {code_summary.get('total_executions', 0)}")
        print(f"   - 执行成功率: {code_summary.get('success_rate', 0):.2%}")
        print(f"   - 自动修复率: {code_summary.get('auto_fix_rate', 0):.2%}")
        print(f"   - 平均执行时间: {code_summary.get('average_execution_time', 0):.2f}秒")
        
        print("\n3. RAG检索指标:")
        rag_summary = report.get("rag_summary", {})
        print(f"   - 总查询次数: {rag_summary.get('total_queries', 0)}")
        print(f"   - 平均检索时间: {rag_summary.get('average_retrieval_time', 0):.3f}秒")
        print(f"   - 平均准确率: {rag_summary.get('average_precision', 0):.2%}")
        print(f"   - 平均召回率: {rag_summary.get('average_recall', 0):.2%}")
        print(f"   - F1分数: {rag_summary.get('f1_score', 0):.2%}")
        
        print("\n4. 用户体验指标:")
        ux_summary = report.get("ux_summary", {})
        print(f"   - 总会话数: {ux_summary.get('total_sessions', 0)}")
        print(f"   - 平均交互次数: {ux_summary.get('average_interactions', 0):.2f}")
        print(f"   - 平均响应时间: {ux_summary.get('average_response_time', 0):.2f}秒")
        print(f"   - 平均满意度: {ux_summary.get('average_satisfaction', 0):.2f}/5")
        
        print("\n5. 资源消耗指标:")
        resource_summary = report.get("resource_summary", {})
        print(f"   - 总Token消耗: {resource_summary.get('total_tokens', 0)}")
        print(f"   - 总API调用次数: {resource_summary.get('total_api_calls', 0)}")
        print(f"   - 平均Token/任务: {resource_summary.get('average_tokens_per_task', 0):.0f}")
        print(f"   - 总成本: ${resource_summary.get('total_cost', 0):.4f}")
        
        print("=" * 60)


# 测试代码
if __name__ == "__main__":
    # 测试评估器
    evaluator = AgentEvaluator()
    
    # 模拟任务评估
    evaluator.start_task("task-001", "问题分析")
    time.sleep(0.1)
    evaluator.end_task("task-001", True)
    
    # 模拟代码执行
    evaluator.record_code_execution(
        "task-001", 
        "print('hello')", 
        0.5, 
        True, 
        output_length=10
    )
    
    # 模拟RAG检索
    evaluator.record_rag_retrieval(
        "task-001",
        "线性规划",
        0.1,
        [{"id": "doc-1", "content": "..."}, {"id": "doc-2", "content": "..."}],
        relevant_ids=["doc-1"]
    )
    
    # 打印摘要
    evaluator.print_summary()
    
    # 保存报告
    evaluator.save_report()
