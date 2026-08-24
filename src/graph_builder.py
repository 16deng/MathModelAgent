"""
LangGraph 图编译器

构建完整的Agent工作流图
"""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

from .graph_state import (
    GraphState,
    ProblemAnalyzer,
    ModelSelector,
    HumanApproval,
    CodeGenerator,
    CodeExecutor,
    CriticAgent,
    PaperGenerator,
    should_continue_to_model_selection,
    should_wait_human_approval,
    should_continue_after_approval,
    should_retry_code,
)


class MathModelGraph:
    """数学建模Agent工作流图"""
    
    def __init__(self, use_checkpoint: bool = True):
        """
        初始化工作流图
        
        Args:
            use_checkpoint: 是否使用检查点持久化
        """
        self.use_checkpoint = use_checkpoint
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """构建工作流图"""
        # 创建状态图
        graph = StateGraph(GraphState)
        
        # 添加节点
        graph.add_node("problem_analyzer", ProblemAnalyzer())
        graph.add_node("model_selector", ModelSelector())
        graph.add_node("human_approval", HumanApproval())
        graph.add_node("code_generator", CodeGenerator())
        graph.add_node("code_executor", CodeExecutor())
        graph.add_node("critic_agent", CriticAgent())
        graph.add_node("paper_generator", PaperGenerator())
        
        # 设置入口
        graph.set_entry_point("problem_analyzer")
        
        # 添加边和条件路由
        graph.add_conditional_edges(
            "problem_analyzer",
            should_continue_to_model_selection,
            {
                "model_selector": "model_selector"
            }
        )
        
        graph.add_conditional_edges(
            "model_selector",
            should_wait_human_approval,
            {
                "human_approval": "human_approval",
                "code_generator": "code_generator"
            }
        )
        
        graph.add_conditional_edges(
            "human_approval",
            should_continue_after_approval,
            {
                "code_generator": "code_generator",
                "human_approval": "human_approval"
            }
        )
        
        graph.add_edge("code_generator", "code_executor")
        graph.add_edge("code_executor", "critic_agent")
        
        graph.add_conditional_edges(
            "critic_agent",
            should_retry_code,
            {
                "code_generator": "code_generator",
                "paper_generator": "paper_generator"
            }
        )
        
        graph.add_edge("paper_generator", END)
        
        return graph
    
    def compile(self):
        """编译工作流图"""
        if self.use_checkpoint:
            # 使用SQLite检查点
            conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
            memory = SqliteSaver(conn)
            return self.graph.compile(
                checkpointer=memory,
                interrupt_before=["human_approval"]  # 在人工审批前中断
            )
        else:
            return self.graph.compile(
                interrupt_before=["human_approval"]
            )
    
    def get_initial_state(self, problem_description: str) -> GraphState:
        """获取初始状态"""
        return {
            "problem_description": problem_description,
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


class GraphRunner:
    """工作流运行器"""
    
    def __init__(self, use_checkpoint: bool = True):
        """初始化运行器"""
        self.builder = MathModelGraph(use_checkpoint)
        self.app = self.builder.compile()
        self.thread_id = "default"
    
    def run(self, problem_description: str, 
            human_decisions: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        运行工作流
        
        Args:
            problem_description: 问题描述
            human_decisions: 人工决策字典
            
        Returns:
            最终状态
        """
        initial_state = self.builder.get_initial_state(problem_description)
        config = {"configurable": {"thread_id": self.thread_id}}
        
        # 运行工作流
        final_state = None
        for event in self.app.stream(initial_state, config):
            for node, state in event.items():
                print(f"[{node}] 阶段完成")
                
                # 处理状态可能是tuple的情况
                if isinstance(state, tuple):
                    state = state[0] if state else {}
                
                if isinstance(state, dict):
                    final_state = state
                    
                    # 检查是否需要人工审批
                    if state.get("is_human_approval_needed"):
                        print("\n>>> 需要人工审批 <<<")
                        if human_decisions and node in human_decisions:
                            print(f"注入人工决策: {human_decisions[node]}")
                        else:
                            print("等待人工决策...")
                            break
        
        return final_state
    
    def resume(self, human_decision: str) -> Dict[str, Any]:
        """
        恢复工作流（注入人工决策后继续）
        
        Args:
            human_decision: 人工决策
            
        Returns:
            最终状态
        """
        config = {"configurable": {"thread_id": self.thread_id}}
        
        # 注入人工决策并继续
        final_state = None
        for event in self.app.stream(
            {"human_decision": human_decision}, 
            config
        ):
            for node, state in event.items():
                print(f"[{node}] 阶段完成")
                final_state = state
        
        return final_state
    
    def get_state(self) -> Optional[Dict[str, Any]]:
        """获取当前状态"""
        config = {"configurable": {"thread_id": self.thread_id}}
        try:
            return self.app.get_state(config)
        except Exception:
            return None


# ============== 测试代码 ==============

if __name__ == "__main__":
    print("=" * 60)
    print("测试 LangGraph 工作流")
    print("=" * 60)
    
    # 创建运行器（不使用检查点）
    runner = GraphRunner(use_checkpoint=False)
    
    # 运行工作流
    problem = """
    某工厂生产两种产品A和B，每种产品需要经过两道工序。
    产品A每件利润3元，产品B每件利润5元。
    工序1每天可用工时12小时，工序2每天可用工时8小时。
    产品A每件需要工序1耗时2小时、工序2耗时1小时。
    产品B每件需要工序1耗时4小时、工序2耗时2小时。
    求使利润最大化的生产方案。
    """
    
    print("\n开始运行工作流...")
    print("-" * 40)
    
    # 运行，注入人工决策
    result = runner.run(
        problem, 
        human_decisions={"model_selector": "线性规划"}
    )
    
    print("-" * 40)
    print("\n工作流运行完成！")
    
    if result:
        print(f"\n最终阶段: {result.get('current_phase')}")
        print(f"选定模型: {result.get('selected_model')}")
        print(f"评审轮次: {result.get('review_rounds')}")
        print(f"资产数量: {len(result.get('artifacts', []))}")
        print(f"论文章节: {list(result.get('paper_sections', {}).keys())}")
    
    print("\n" + "=" * 60)
    print("LangGraph 工作流测试完成！")
    print("=" * 60)
