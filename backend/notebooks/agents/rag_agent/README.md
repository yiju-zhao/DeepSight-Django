# RAG Agent - ReAct 架构说明

## 概述

这个 RAG Agent 使用 **ReAct (Reasoning + Acting)** 模式，通过迭代推理和检索来回答问题。

## 🔄 调用流程

### 1. 入口：chat_service.py

```python
# chat_service.py: create_session_chat_stream()
from notebooks.agents.rag_agent.graph import create_rag_agent
from notebooks.agents.rag_agent.config import RAGAgentConfig

# 创建配置
config = RAGAgentConfig(
    model_name="gpt-5",
    api_key=api_key,
    retrieval_service=retrieval_service,  # 注入检索服务
    dataset_ids=["dataset_id"],
    max_iterations=5,
)

# 创建 agent
agent = create_rag_agent(config)

# 初始化状态
initial_state = {
    "question": "用户问题",
    "message_history": [],
    "reasoning_steps": [],
    "executed_queries": [],
    "current_retrieved": [],
    "retrieved_chunks": [],
    "iteration": 0,
    "final_answer": "",
}

# 执行（流式）
async for event in agent.astream(initial_state):
    # 处理事件
    for node_name, node_state in event.items():
        # 显示状态更新
        ...

# 或执行（非流式）
final_state = await agent.ainvoke(initial_state)
final_answer = final_state["final_answer"]
```

---

### 2. Agent 创建：graph.py

```python
# graph.py: create_rag_agent()
def create_rag_agent(config: RAGAgentConfig):
    # 初始化模型
    chat_model = init_chat_model(
        model=f"openai:{config.model_name}",
        api_key=config.api_key,
        temperature=config.temperature,
    )

    # 定义节点
    def reasoning_node(state): ...
    def retrieval_node(state): ...
    def evaluation_node(state): ...
    def synthesize_node(state): ...

    # 构建图
    graph = StateGraph(RAGReActState)
    graph.add_node("reasoning", reasoning_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("evaluation", evaluation_node)
    graph.add_node("synthesize", synthesize_node)

    # 添加边（控制流）
    graph.add_conditional_edges("reasoning", should_retrieve, {...})
    graph.add_edge("retrieval", "evaluation")
    graph.add_conditional_edges("evaluation", should_continue_reasoning, {...})
    graph.add_edge("synthesize", END)

    return graph.compile()
```

---

### 3. ReAct 循环流程

```
用户问题
  ↓
┌─────────────────── ReAct Loop (最多 5 轮) ────────────────────┐
│                                                                │
│  【reasoning_node】                                             │
│    - 使用 REASON_PROMPT 让 LLM 思考                             │
│    - LLM 生成推理过程并输出查询（包裹在特殊标记中）                │
│    - 提取查询：extract_between(output, BEGIN_SEARCH_QUERY, END) │
│    - 更新 state.current_queries                                │
│                                                                │
│  ↓                                                             │
│                                                                │
│  【should_retrieve 条件判断】                                    │
│    - 如果有查询 → 进入 retrieval                                 │
│    - 如果无查询 → 跳到 synthesize                                │
│                                                                │
│  ↓                                                             │
│                                                                │
│  【retrieval_node】 ← 这里调用 retrieval 工具                    │
│    - 遍历所有 current_queries                                   │
│    - 对每个查询：                                                │
│      ① 检查去重（executed_queries）                              │
│      ② 调用 config.retrieval_service.retrieve_chunks()          │
│         参数：                                                   │
│           - question: query                                    │
│           - dataset_ids: config.dataset_ids                    │
│           - similarity_threshold: config.similarity_threshold  │
│           - top_k: config.top_k                                │
│      ③ 提取 chunks 并转换为 dict 格式                            │
│      ④ 添加到 all_retrieved                                     │
│    - 更新 state.current_retrieved 和 retrieved_chunks           │
│                                                                │
│  ↓                                                             │
│                                                                │
│  【evaluation_node】                                            │
│    - 格式化检索结果：format_chunks(current_retrieved)            │
│    - 截断历史：truncate_reasoning_history(reasoning_steps)      │
│    - 使用 RELEVANT_EXTRACTION_PROMPT 让 LLM 评估                │
│    - LLM 提取强相关信息，过滤无关内容                             │
│    - 将评估结果包裹在 BEGIN_SEARCH_RESULT 标记中                  │
│    - 添加到 message_history 和 reasoning_steps                  │
│                                                                │
│  ↓                                                             │
│                                                                │
│  【should_continue_reasoning 条件判断】                          │
│    - 如果达到 max_iterations → finish                           │
│    - 如果 LLM 说 "sufficient information" → finish             │
│    - 否则 → continue（回到 reasoning_node）                      │
│                                                                │
└────────────────────────────────────────────────────────────────┘
  ↓

【synthesize_node】
  - 合并所有 reasoning_steps
  - 使用 SYNTHESIS_PROMPT 生成最终答案
  - 返回 final_answer
  ↓
返回给用户
```

---

## 🔧 Retrieval 工具调用详解

### retrieval_node 中的调用

```python
# graph.py: retrieval_node()
async def retrieval_node(state: RAGReActState) -> RAGReActState:
    queries = state["current_queries"]
    all_retrieved = []

    for query in queries:
        # 去重检查
        if query in state["executed_queries"]:
            continue

        # 调用检索服务
        result = config.retrieval_service.retrieve_chunks(
            question=query,                                    # 查询字符串
            dataset_ids=config.dataset_ids,                   # ["dataset_id_1", ...]
            similarity_threshold=config.similarity_threshold, # 0.4
            top_k=config.top_k,                               # 10
        )

        # 提取 chunks（result 是 RetrievalResult 对象）
        chunks = result.chunks  # List[ChunkResponse]

        # 转换为 dict 格式
        for chunk in chunks:
            chunk_dict = {
                "chunk_id": chunk.id,
                "doc_name": chunk.doc_name,
                "content": chunk.content,
                "similarity": chunk.similarity,
            }
            all_retrieved.append(chunk_dict)

    # 更新状态
    return {
        **state,
        "current_retrieved": all_retrieved,
        "retrieved_chunks": state["retrieved_chunks"] + all_retrieved,
        "executed_queries": state["executed_queries"] + queries,
    }
```

---

### RetrievalService API

```python
# retrieval_service.py
class RetrievalService:
    def retrieve_chunks(
        self,
        question: str,              # 查询问题
        dataset_ids: list[str],     # 数据集 ID 列表
        similarity_threshold: float = 0.2,  # 相似度阈值
        top_k: int = 6,             # 返回数量
    ) -> RetrievalResult:
        """
        调用 RAGFlow API 检索文档块。

        Returns:
            RetrievalResult with:
                - chunks: List[ChunkResponse]
                - total_chunks: int
        """
        # 调用 RAGFlow API
        response = self.ragflow_service.retrieve(
            dataset_ids=dataset_ids,
            question=question,
            similarity_threshold=similarity_threshold,
            limit=top_k,
        )

        # 解析并返回结果
        return RetrievalResult(
            chunks=[ChunkResponse(...) for chunk in response.chunks],
            total_chunks=len(response.chunks)
        )
```

---

### 数据流

```
config.retrieval_service (注入)
  ↓
retrieval_node 调用
  ↓
config.retrieval_service.retrieve_chunks(
    question="深度学习;医疗影像;诊断",
    dataset_ids=["kb_medical"],
    similarity_threshold=0.4,
    top_k=10
)
  ↓
RetrievalResult {
    chunks: [
        ChunkResponse(
            id="chunk_001",
            doc_name="医疗AI研究报告.pdf",
            content="深度学习在医疗影像诊断中...",
            similarity=0.92
        ),
        ...
    ]
}
  ↓
转换为 dict 格式
  ↓
state["current_retrieved"] = [
    {
        "chunk_id": "chunk_001",
        "doc_name": "医疗AI研究报告.pdf",
        "content": "深度学习在医疗影像诊断中...",
        "similarity": 0.92
    },
    ...
]
  ↓
传递给 evaluation_node 进行 LLM 评估
```

---

## 📝 配置参数

### RAGAgentConfig

```python
@dataclass
class RAGAgentConfig:
    # 模型
    model_name: str = "gpt-5"
    api_key: Optional[str] = None

    # 温度（不同阶段）
    temperature: float = 0.7           # Reasoning
    eval_temperature: float = 0.1      # Evaluation
    synthesis_temperature: float = 0.3 # Synthesis

    # ReAct 循环
    max_iterations: int = 5

    # 检索参数
    retrieval_service: Optional[object] = None
    dataset_ids: list[str] = []
    similarity_threshold: float = 0.4  # 从 0.2 提升到 0.4
    top_k: int = 10                    # 从 6 提升到 10

    # 历史管理
    keep_first_n_steps: int = 1
    keep_last_n_steps: int = 4
```

---

## 🎯 关键改进点

### 1. 无需单独的 Tool 定义
- **旧架构**：需要定义 LangChain @tool，Agent 调用 tool
- **新架构**：直接在 retrieval_node 中调用 retrieval_service

### 2. Agent 自主生成查询
- **旧架构**：小模型（gpt-4.1-mini）预处理查询
- **新架构**：主模型（gpt-5）在推理过程中生成查询

### 3. 强相关性过滤
- **旧架构**：无过滤，直接使用所有检索结果
- **新架构**：evaluation_node 使用 LLM 评估并过滤

### 4. 迭代优化
- **旧架构**：单次检索
- **新架构**：最多 5 轮，根据结果质量决定是否继续

---

## 🔍 调试技巧

### 查看日志
```python
# graph.py 中有详细日志
logger.info(f"[retrieval_node] Retrieved {len(chunks)} chunks for query: {query}")
logger.info(f"[reasoning_node] Extracted {len(queries)} queries: {queries}")
```

### 检查状态
```python
final_state = await agent.ainvoke(initial_state)

print("执行的查询:", final_state["executed_queries"])
print("迭代次数:", final_state["iteration"])
print("检索到的文档数:", len(final_state["retrieved_chunks"]))
print("推理步骤:")
for i, step in enumerate(final_state["reasoning_steps"], 1):
    print(f"\nStep {i}:")
    print(step[:200] + "...")
```

### 测试单个节点
```python
# 测试 retrieval_node
test_state = {
    "current_queries": ["深度学习;医疗"],
    "executed_queries": [],
    "current_retrieved": [],
    "retrieved_chunks": [],
    ...
}

result = await retrieval_node(test_state)
print("检索结果:", result["current_retrieved"])
```

---

## 📚 相关文件

- `states.py` - RAGReActState 定义
- `prompts.py` - REASON_PROMPT、RELEVANT_EXTRACTION_PROMPT、SYNTHESIS_PROMPT
- `graph.py` - ReAct 循环节点和逻辑
- `config.py` - RAGAgentConfig 配置
- `utils.py` - 辅助函数
- `test_react.py` - 测试脚本

---

## 🚀 使用示例

### 基础调用
```python
from notebooks.agents.rag_agent import create_rag_agent, RAGAgentConfig
from notebooks.services.retrieval_service import RetrievalService

# 初始化
retrieval_service = RetrievalService(ragflow_service)
config = RAGAgentConfig(
    model_name="gpt-5",
    api_key="sk-...",
    retrieval_service=retrieval_service,
    dataset_ids=["medical_kb"],
)

agent = create_rag_agent(config)

# 执行
initial_state = {
    "question": "深度学习在医疗影像诊断中的应用效果如何？",
    "message_history": [],
    "reasoning_steps": [],
    "executed_queries": [],
    "current_reasoning": "",
    "current_queries": [],
    "current_retrieved": [],
    "retrieved_chunks": [],
    "iteration": 0,
    "final_answer": "",
    "should_continue": True,
}

final_state = await agent.ainvoke(initial_state)
print(final_state["final_answer"])
```

### 流式调用
```python
async for event in agent.astream(initial_state):
    for node_name, node_state in event.items():
        if node_name == "reasoning":
            print(f"🤔 思考中（第 {node_state['iteration']} 轮）...")
        elif node_name == "retrieval":
            print(f"🔍 检索: {node_state['current_queries']}")
        elif node_name == "evaluation":
            print("📊 分析结果...")
        elif node_name == "synthesize":
            print("✍️ 生成答案...")
```

---

## ⚠️ 常见问题

### 1. 检索失败
- 检查 `retrieval_service` 是否正确初始化
- 检查 `dataset_ids` 是否存在
- 查看日志中的详细错误信息

### 2. 无限循环
- 检查 `max_iterations` 设置
- 查看 `should_continue_reasoning` 的条件判断
- Agent 可能无法找到 "sufficient information" 信号

### 3. 结果质量差
- 调整 `similarity_threshold`（提高过滤）
- 增加 `top_k`（扩大候选集）
- 检查 REASON_PROMPT 和 RELEVANT_EXTRACTION_PROMPT

---

**完成时间：** 2025-12-11
**架构：** ReAct (Reasoning + Acting)
**模型：** GPT-5
