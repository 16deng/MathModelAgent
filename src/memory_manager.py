"""
记忆管理模块

实现优化的记忆系统，包括：
- 记忆价值评估
- 分层索引
- 按需加载
- 并行选取
- 监测机制
"""

import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from enum import Enum


class MemoryLayer(Enum):
    """记忆层级"""
    HOT = "hot"      # 热记忆：频繁使用，内存中
    WARM = "warm"    # 温记忆：偶尔使用，快速索引
    COLD = "cold"    # 冷记忆：很少使用，归档存储


@dataclass
class Memory:
    """记忆数据"""
    memory_id: str
    content: str
    embedding: Optional[List[float]] = None
    created_at: str = ""
    last_accessed: str = ""
    access_count: int = 0
    value_score: float = 0.0
    layer: MemoryLayer = MemoryLayer.WARM
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "embedding": self.embedding,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "value_score": self.value_score,
            "layer": self.layer.value,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """从字典创建"""
        data['layer'] = MemoryLayer(data['layer'])
        return cls(**data)


class MemoryValueEvaluator:
    """记忆价值评估器"""
    
    def __init__(self):
        """初始化评估器"""
        self.frequency_weight = 0.3
        self.recency_weight = 0.3
        self.relevance_weight = 0.4
    
    def evaluate(self, memory: Memory, current_context: Optional[str] = None) -> float:
        """
        评估记忆价值
        
        Args:
            memory: 记忆数据
            current_context: 当前上下文
            
        Returns:
            价值分数 (0-1)
        """
        # 频率分数
        frequency_score = min(memory.access_count / 10, 1.0)
        
        # 时间衰减分数
        if memory.last_accessed:
            last_accessed = datetime.fromisoformat(memory.last_accessed)
            days_since = (datetime.now() - last_accessed).days
            recency_score = max(0, 1 - days_since / 30)
        else:
            recency_score = 0.5
        
        # 相关性分数（简化：基于内容长度）
        relevance_score = min(len(memory.content) / 500, 1.0)
        
        # 计算总分
        value_score = (
            frequency_score * self.frequency_weight +
            recency_score * self.recency_weight +
            relevance_score * self.relevance_weight
        )
        
        return value_score


class MemoryIndex:
    """记忆索引"""
    
    def __init__(self, index_dir: str = "./memory_index"):
        """
        初始化索引
        
        Args:
            index_dir: 索引目录
        """
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # 分层存储
        self.hot_memories: Dict[str, Memory] = {}
        self.warm_memories: Dict[str, Memory] = {}
        self.cold_memories: Dict[str, Memory] = {}
        
        # 加载索引
        self._load_index()
    
    def _load_index(self):
        """加载索引"""
        for layer in MemoryLayer:
            index_file = self.index_dir / f"{layer.value}_index.json"
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    memories = {k: Memory.from_dict(v) for k, v in data.items()}
                    
                    if layer == MemoryLayer.HOT:
                        self.hot_memories = memories
                    elif layer == MemoryLayer.WARM:
                        self.warm_memories = memories
                    else:
                        self.cold_memories = memories
    
    def _save_index(self, layer: MemoryLayer):
        """保存索引"""
        if layer == MemoryLayer.HOT:
            memories = self.hot_memories
        elif layer == MemoryLayer.WARM:
            memories = self.warm_memories
        else:
            memories = self.cold_memories
        
        index_file = self.index_dir / f"{layer.value}_index.json"
        data = {k: v.to_dict() for k, v in memories.items()}
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_memory(self, memory: Memory):
        """添加记忆"""
        if memory.layer == MemoryLayer.HOT:
            self.hot_memories[memory.memory_id] = memory
            self._save_index(MemoryLayer.HOT)
        elif memory.layer == MemoryLayer.WARM:
            self.warm_memories[memory.memory_id] = memory
            self._save_index(MemoryLayer.WARM)
        else:
            self.cold_memories[memory.memory_id] = memory
            self._save_index(MemoryLayer.COLD)
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        if memory_id in self.hot_memories:
            return self.hot_memories[memory_id]
        elif memory_id in self.warm_memories:
            return self.warm_memories[memory_id]
        elif memory_id in self.cold_memories:
            return self.cold_memories[memory_id]
        return None
    
    def search_by_keywords(self, keywords: List[str], 
                           max_results: int = 5) -> List[Memory]:
        """按关键词搜索"""
        results = []
        all_memories = {**self.hot_memories, **self.warm_memories, **self.cold_memories}
        
        for memory in all_memories.values():
            if any(keyword.lower() in memory.content.lower() for keyword in keywords):
                results.append(memory)
        
        # 按价值分数排序
        results.sort(key=lambda m: m.value_score, reverse=True)
        return results[:max_results]
    
    def get_all_memories(self) -> List[Memory]:
        """获取所有记忆"""
        all_memories = {**self.hot_memories, **self.warm_memories, **self.cold_memories}
        return list(all_memories.values())


class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, memory_dir: str = "./memory"):
        """
        初始化记忆管理器
        
        Args:
            memory_dir: 记忆存储目录
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.index = MemoryIndex(str(self.memory_dir / "index"))
        self.evaluator = MemoryValueEvaluator()
        
        # 监测指标
        self.metrics = {
            "total_memories": 0,
            "hot_memories": 0,
            "warm_memories": 0,
            "cold_memories": 0,
            "retrieval_count": 0,
            "hit_count": 0,
            "avg_retrieval_time": 0
        }
    
    def add_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        添加记忆
        
        Args:
            content: 记忆内容
            metadata: 元数据
            
        Returns:
            记忆ID
        """
        memory_id = hashlib.sha256(content.encode()).hexdigest()[:12]
        
        memory = Memory(
            memory_id=memory_id,
            content=content,
            created_at=datetime.now().isoformat(),
            last_accessed=datetime.now().isoformat(),
            access_count=0,
            value_score=0.0,
            layer=MemoryLayer.WARM,
            metadata=metadata or {}
        )
        
        self.index.add_memory(memory)
        self._update_metrics()
        
        return memory_id
    
    def retrieve_memory(self, query: str, max_results: int = 3) -> List[Memory]:
        """
        检索记忆
        
        Args:
            query: 查询文本
            max_results: 最大结果数
            
        Returns:
            相关记忆列表
        """
        start_time = time.time()
        
        # 提取关键词
        keywords = query.split()
        
        # 搜索记忆
        results = self.index.search_by_keywords(keywords, max_results)
        
        # 更新访问信息
        for memory in results:
            memory.access_count += 1
            memory.last_accessed = datetime.now().isoformat()
            memory.value_score = self.evaluator.evaluate(memory, query)
        
        # 更新监测指标
        retrieval_time = time.time() - start_time
        self.metrics["retrieval_count"] += 1
        self.metrics["hit_count"] += len(results)
        self.metrics["avg_retrieval_time"] = (
            (self.metrics["avg_retrieval_time"] * (self.metrics["retrieval_count"] - 1) + retrieval_time) 
            / self.metrics["retrieval_count"]
        )
        
        return results
    
    def update_memory_layer(self, memory_id: str, new_layer: MemoryLayer):
        """更新记忆层级"""
        memory = self.index.get_memory(memory_id)
        if memory:
            memory.layer = new_layer
            self.index.add_memory(memory)
            self._update_metrics()
    
    def cleanup_low_value_memories(self, threshold: float = 0.3):
        """清理低价值记忆"""
        all_memories = self.index.get_all_memories()
        
        for memory in all_memories:
            if memory.value_score < threshold:
                # 移动到冷记忆层
                memory.layer = MemoryLayer.COLD
                self.index.add_memory(memory)
        
        self._update_metrics()
    
    def _update_metrics(self):
        """更新监测指标"""
        self.metrics["total_memories"] = (
            len(self.index.hot_memories) + 
            len(self.index.warm_memories) + 
            len(self.index.cold_memories)
        )
        self.metrics["hot_memories"] = len(self.index.hot_memories)
        self.metrics["warm_memories"] = len(self.index.warm_memories)
        self.metrics["cold_memories"] = len(self.index.cold_memories)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取监测指标"""
        return self.metrics
    
    def print_metrics(self):
        """打印监测指标"""
        print("=" * 50)
        print("记忆系统监测指标")
        print("=" * 50)
        print(f"总记忆数: {self.metrics['total_memories']}")
        print(f"热记忆: {self.metrics['hot_memories']}")
        print(f"温记忆: {self.metrics['warm_memories']}")
        print(f"冷记忆: {self.metrics['cold_memories']}")
        print(f"检索次数: {self.metrics['retrieval_count']}")
        print(f"命中次数: {self.metrics['hit_count']}")
        print(f"平均检索时间: {self.metrics['avg_retrieval_time']:.3f}秒")
        print("=" * 50)


# 测试代码
if __name__ == "__main__":
    # 测试记忆管理器
    manager = MemoryManager()
    
    # 添加记忆
    manager.add_memory("线性规划是数学规划的一个重要分支")
    manager.add_memory("旅行商问题是组合优化中的经典问题")
    manager.add_memory("遗传算法是一种启发式搜索算法")
    
    # 检索记忆
    results = manager.retrieve_memory("线性规划")
    print(f"检索结果: {len(results)} 条")
    for memory in results:
        print(f"  - {memory.content[:50]}...")
    
    # 打印监测指标
    manager.print_metrics()
