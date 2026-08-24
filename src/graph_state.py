"""
基于LangGraph的有状态状态机

实现黑板模式（Blackboard State）、断点与检查点、中断式人机协同
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import operator


# ============== 黑板模式：全局状态结构体 ==============

class SymbolInfo(BaseModel):
    """数学符号信息"""
    name: str
    description: str
    unit: Optional[str] = None
    type: str = "variable"  # variable, constant, parameter


class ModelCandidate(BaseModel):
    """候选模型"""
    name: str
    description: str
    pros: List[str] = []
    cons: List[str] = []
    complexity: str = "medium"  # low, medium, high


class CodeDraft(BaseModel):
    """代码草稿"""
    code: str
    language: str = "python"
    version: int = 1
    is_executed: bool = False
    execution_result: Optional[str] = None
    error_message: Optional[str] = None


class CriticVerdict(BaseModel):
    """评审结论"""
    passed: bool
    score: float = 0.0
    issues: List[str] = []
    suggestions: List[str] = []
    reason: str = ""


class AssetRecord(BaseModel):
    """资产记录"""
    key: str
    value: Any
    type: str  # scalar, figure, table
    source: str  # 来源代码
    timestamp: str = ""


class GraphState(TypedDict):
    """
    黑板模式：全局状态结构体
    
    各Agent节点只通过特定字段通信，避免上下文污染
    """
    # 问题分析相关
    problem_description: str  # 原始问题描述
    problem_type: str  # 问题类型
    symbols: Annotated[List[Dict], operator.add]  # 数学符号
    constraints: Annotated[List[str], operator.add]  # 约束条件
    
    # 模型选型相关
    model_candidates: Annotated[List[Dict], operator.add]  # 候选模型
    selected_model: Optional[str]  # 选定模型
    model_selection_reason: str  # 选型理由
    
    # 代码执行相关
    code_draft: Optional[Dict]  # 代码草稿
    execution_history: Annotated[List[Dict], operator.add]  # 执行历史
    
    # 评审相关
    critic_verdict: Optional[Dict]  # 评审结论
    review_rounds: int  # 评审轮次
    
    # 资产账本
    artifacts: Annotated[List[Dict], operator.add]  # 计算结果和图表
    
    # 论文相关
    paper_sections: Dict[str, str]  # 论文各章节
    
    # 流程控制
    current_phase: str  # 当前阶段
    is_human_approval_needed: bool  # 是否需要人工审批
    human_decision: Optional[str]  # 人工决策
    error_log: Annotated[List[str], operator.add]  # 错误日志


# ============== 状态节点定义 ==============

class StateNode:
    """状态节点基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    def __call__(self, state: GraphState) -> Dict[str, Any]:
        raise NotImplementedError


class ProblemAnalyzer(StateNode):
    """问题分析节点"""
    
    def __init__(self):
        super().__init__("problem_analyzer")
    
    def __call__(self, state: GraphState) -> Dict[str, Any]:
        """分析问题，提取符号和约束"""
        problem = state["problem_description"]
        
        # 模拟问题分析（实际应调用LLM）
        symbols = [
            {"name": "x", "description": "决策变量", "type": "variable"},
            {"name": "f(x)", "description": "目标函数", "type": "function"},
        ]
        
        constraints = [
            "x >= 0",
            "sum(x) <= budget"
        ]
        
        problem_type = "optimization"  # 应由LLM判断
        
        return {
            "symbols": symbols,
            "constraints": constraints,
            "problem_type": problem_type,
            "current_phase": "model_selection"
        }


class ModelSelector(StateNode):
    """模型选型节点 - 需要人工审批"""
    
    def __init__(self):
        super().__init__("model_selector")
    
    def __call__(self, state: GraphState) -> Dict[str, Any]:
        """推荐候选模型，等待人工选择"""
        problem_type = state.get("problem_type", "optimization")
        
        # 生成候选模型
        candidates = [
            {
                "name": "线性规划",
                "description": "适用于线性目标函数和约束",
                "pros": ["求解快速", "全局最优"],
                "cons": ["仅限线性问题"],
                "complexity": "low"
            },
            {
                "name": "整数规划",
                "description": "适用于离散决策变量",
                "pros": ["处理离散变量"],
                "cons": ["计算复杂度高"],
                "complexity": "high"
            }
        ]
        
        # 标记需要人工审批
        return {
            "model_candidates": candidates,
            "is_human_approval_needed": True,
            "current_phase": "human_approval"
        }


class HumanApproval(StateNode):
    """人工审批节点"""
    
    def __init__(self):
        super().__init__("human_approval")
    
    def __call__(self, state: GraphState) -> Dict[str, Any]:
        """等待人工审批"""
        human_decision = state.get("human_decision")
        
        if human_decision:
            # 人工已做出决策
            return {
                "selected_model": human_decision,
                "is_human_approval_needed": False,
                "current_phase": "code_generation"
            }
        else:
            # 继续等待
            return {
                "is_human_approval_needed": True,
                "current_phase": "human_approval"
            }


class CodeGenerator(StateNode):
    """代码生成节点"""
    
    def __init__(self):
        super().__init__("code_generator")
    
    def __call__(self, state: GraphState) -> Dict[str, Any]:
        """生成求解代码"""
        selected_model = state.get("selected_model", "线性规划")
        symbols = state.get("symbols", [])
        
        # 生成代码（实际应调用LLM）
        code_draft = {
            "code": f"""
import numpy as np
from scipy.optimize import linprog

# 目标函数系数
c = [1, 2]

# 不等式约束
A_ub = [[-1, -1]]
b_ub = [-10]

# 求解
result = linprog(c, A_ub=A_ub, b_ub=b_ub)
print(f"最优解: {{result.x}}")
print(f"最优值: {{result.fun}}")
""",
            "language": "python",
            "version": 1,
            "is_executed": False
        }
        
        return {
            "code_draft": code_draft,
            "current_phase": "code_execution"
        }


class CodeExecutor(StateNode):
    """代码执行节点"""
    
    def __init__(self):
        super().__init__("code_executor")
    
    def __call__(self, state: GraphState) -> Dict[str, Any]:
        """执行代码"""
        code_draft = state.get("code_draft", {})
        
        # 模拟执行（实际应使用Jupyter内核）
        execution_record = {
            "code": code_draft.get("code", ""),
            "status": "success",
            "output": "最优解: [10.  0.]\n最优值: 10.0",
            "timestamp": datetime.now().isoformat()
        }
        
        # 记录资产
        artifact = {
            "key": "optimal_value",
            "value": 10.0,
            "type": "scalar",
            "source": "linprog",
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "execution_history": [execution_record],
            "artifacts": [artifact],
            "current_phase": "critic_review"
        }


class CriticAgent(StateNode):
    """评审Agent节点"""
    
    def __init__(self):
        super().__init__("critic_agent")
    
    def __call__(self, state: GraphState) -> Dict[str, Any]:
        """评审代码和结果"""
        execution_history = state.get("execution_history", [])
        artifacts = state.get("artifacts", [])
        review_rounds = state.get("review_rounds", 0)
        
        # 模拟评审
        verdict = {
            "passed": True,
            "score": 85.0,
            "issues": [],
            "suggestions": ["可以添加灵敏度分析"],
            "reason": "代码执行成功，结果合理"
        }
        
        # 判断是否需要回退
        if not verdict["passed"] and review_rounds < 3:
            # 回退到代码生成
            return {
                "critic_verdict": verdict,
                "review_rounds": review_rounds + 1,
                "current_phase": "code_generation",
                "error_log": [f"评审未通过: {verdict['reason']}"]
            }
        
        return {
            "critic_verdict": verdict,
            "review_rounds": review_rounds + 1,
            "current_phase": "paper_generation"
        }


class PaperGenerator(StateNode):
    """论文生成节点"""
    
    def __init__(self):
        super().__init__("paper_generator")
    
    def __call__(self, state: GraphState) -> Dict[str, Any]:
        """生成论文"""
        symbols = state.get("symbols", [])
        artifacts = state.get("artifacts", [])
        selected_model = state.get("selected_model", "")
        
        # 生成论文章节
        paper_sections = {
            "abstract": "本文研究了...",
            "problem_analysis": "问题分析...",
            "model_establishment": f"采用{selected_model}模型...",
            "solution": "求解过程...",
            "conclusion": "结论..."
        }
        
        return {
            "paper_sections": paper_sections,
            "current_phase": "completed"
        }


# ============== 条件路由函数 ==============

def should_continue_to_model_selection(state: GraphState) -> str:
    """是否继续到模型选型"""
    if state.get("problem_type"):
        return "model_selector"
    return "problem_analyzer"


def should_wait_human_approval(state: GraphState) -> str:
    """是否等待人工审批"""
    if state.get("is_human_approval_needed"):
        return "human_approval"
    return "code_generator"


def should_continue_after_approval(state: GraphState) -> str:
    """人工审批后继续"""
    if state.get("selected_model"):
        return "code_generator"
    return "human_approval"


def should_retry_code(state: GraphState) -> str:
    """是否重试代码"""
    critic_verdict = state.get("critic_verdict", {})
    review_rounds = state.get("review_rounds", 0)
    
    if not critic_verdict.get("passed") and review_rounds < 3:
        return "code_generator"
    return "paper_generator"


# ============== 测试代码 ==============

if __name__ == "__main__":
    print("=" * 60)
    print("测试 GraphState 状态机")
    print("=" * 60)
    
    # 测试状态初始化
    initial_state: GraphState = {
        "problem_description": "某工厂需要优化生产计划...",
        "problem_type": "",
        "symbols": [],
        "constraints": [],
        "model_candidates": [],
        "selected_model": None,
        "model_selection_reason": "",
        "code_draft": None,
        "execution_history": [],
        "critic_verdict": None,
        "review_rounds": 0,
        "artifacts": [],
        "paper_sections": {},
        "current_phase": "problem_analysis",
        "is_human_approval_needed": False,
        "human_decision": None,
        "error_log": []
    }
    
    print(f"\n初始状态: {initial_state['current_phase']}")
    
    # 测试问题分析
    analyzer = ProblemAnalyzer()
    state_update = analyzer(initial_state)
    print(f"问题分析后: {state_update.get('current_phase')}")
    print(f"提取符号: {state_update.get('symbols')}")
    
    # 测试模型选型
    selector = ModelSelector()
    state_update = selector({**initial_state, **state_update})
    print(f"\n模型选型后: {state_update.get('current_phase')}")
    print(f"候选模型数: {len(state_update.get('model_candidates', []))}")
    print(f"需要人工审批: {state_update.get('is_human_approval_needed')}")
    
    # 测试人工审批
    approver = HumanApproval()
    state_with_decision = {
        **initial_state,
        **state_update,
        "human_decision": "线性规划"
    }
    state_update = approver(state_with_decision)
    print(f"\n人工审批后: {state_update.get('current_phase')}")
    print(f"选定模型: {state_update.get('selected_model')}")
    
    # 测试代码生成
    generator = CodeGenerator()
    state_update = generator({**initial_state, **state_update})
    print(f"\n代码生成后: {state_update.get('current_phase')}")
    print(f"代码长度: {len(state_update.get('code_draft', {}).get('code', ''))}")
    
    # 测试代码执行
    executor = CodeExecutor()
    state_update = executor({**initial_state, **state_update})
    print(f"\n代码执行后: {state_update.get('current_phase')}")
    print(f"执行历史数: {len(state_update.get('execution_history', []))}")
    print(f"资产记录数: {len(state_update.get('artifacts', []))}")
    
    # 测试评审
    critic = CriticAgent()
    state_update = critic({**initial_state, **state_update})
    print(f"\n评审后: {state_update.get('current_phase')}")
    print(f"评审结论: {state_update.get('critic_verdict', {}).get('passed')}")
    
    # 测试论文生成
    paper_gen = PaperGenerator()
    state_update = paper_gen({**initial_state, **state_update})
    print(f"\n论文生成后: {state_update.get('current_phase')}")
    print(f"论文章节数: {len(state_update.get('paper_sections', {}))}")
    
    print("\n" + "=" * 60)
    print("GraphState 测试完成！")
    print("=" * 60)
