在构建生产级 AI Agent 时，JSON 的结构设计决定了系统的稳定性和可扩展性。我们可以将 **Manifest** 视为“技能字典”，而 **Interaction JSON** 则是 Agent 与模型之间的“对话协议”。

***

## 1. Manifest.json 是如何被使用的？

`manifest.json` 并不是直接发给大模型的，它是 **Agent 后端程序的配置表**。它的核心逻辑是：**“按需加载，动态路由”**。

### 使用生命周期：

1. **加载阶段 (Loading)**：Agent 启动时扫描 `skills/` 目录，读取所有 `manifest.json`，构建一个内存中的**技能索引表**。
2. **路由阶段 (Discovery)**：当用户输入时，Agent 后端提取所有 `manifest.json` 中的 `name` 和 `description`，拼接到路由器的 System Prompt 中。
3. **注入阶段 (Injection)**：一旦模型选中某个 `skill_id`，后端程序根据 `manifest` 里的路径找到对应的 `instructions.md`（SOP），将其作为上下文喂给模型。

***

## 2. 第一次交互：意图路由 (Router)

**目标：** 让模型在多个技能中选出一个，并解释原因。

### Request JSON (Agent -> LLM)

JSON

```json
{
  "model": "gemini-2.0-flash",
  "messages": [
    {
      "role": "system",
      "content": "你是一个调度员。技能库如下：\n- [Legal]: 合规审查\n- [Finance]: 财务审计\n请调用 activate_skill 选择。"
    },
    { "role": "user", "content": "这篇合同的税务条款有风险吗？" }
  ],
  "tools": [{
    "type": "function",
    "function": {
      "name": "activate_skill",
      "parameters": {
        "type": "object",
        "properties": {
          "skill_id": { "type": "string", "enum": ["Legal", "Finance"] }
        },
        "required": ["skill_id"]
      }
    }
  }]
}
```

### Response JSON (LLM -> Agent)

JSON

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "tool_calls": [{
        "id": "call_123",
        "type": "function",
        "function": {
          "name": "activate_skill",
          "arguments": "{\"skill_id\": \"Legal\"}"
        }
      }]
    }
  }]
}
```

***

## 3. 第二次交互：技能激活与 SOP 注入

**动作：** 后端接收到 `Legal` 指令，查表找到 `Legal` 技能的详细操作规范，开始真正干活。

### Request JSON (Agent -> LLM)

此时历史记录中加入了 `activate_skill` 的**执行结果**（即该技能的详细指南）。

JSON

```json
{
  "model": "gemini-2.0-flash",
  "messages": [
    { "role": "system", "content": "...(调度员指令)..." },
    { "role": "user", "content": "这篇合同的税务条款有风险吗？" },
    { "role": "assistant", "tool_calls": [{ "id": "call_123", "function": { "name": "activate_skill", "arguments": "{\"skill_id\": \"Legal\"}" } }] },
    {
      "role": "tool",
      "tool_call_id": "call_123",
      "content": "【Legal 技能激活】详细 SOP：1. 必须调用 read_contract 读取全文；2. 检索关键字 'Tax'；3. 给出风险评分。"
    }
  ],
  "tools": [
    { "type": "function", "function": { "name": "read_contract", "parameters": { "type": "object", "properties": { "file_id": { "type": "string" } } } } }
  ]
}
```

### Response JSON (LLM -> Agent)

模型看到了 SOP，立刻执行第一个动作。

JSON

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "tool_calls": [{
        "id": "call_456",
        "function": { "name": "read_contract", "arguments": "{\"file_id\": \"doc_001\"}" }
      }]
    }
  }]
}
```

***

## 4. 第三次交互：环境反馈与任务终结

**动作：** 后端读取文件并返回。

### Request JSON (Agent -> LLM)

JSON

```json
{
  "messages": [
    "...(省略中间所有上下文)...",
    { "role": "assistant", "tool_calls": [{ "id": "call_456", "function": { "name": "read_contract", "arguments": "..." } }] },
    {
      "role": "tool",
      "tool_call_id": "call_456",
      "content": "合同第12条：所有税费由乙方承担，且不包含增值税..."
    }
  ]
}
```

### Response JSON (LLM -> Agent)

模型结合 SOP 规范和文件内容，给出最终专业结论。

JSON

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "根据 Legal 技能规范，分析如下：\n- **风险点**：增值税未包含在总价中，可能导致成本超支 13%。\n- **风险评分**：高风险。\n建议：要求甲方明确含税价。"
    }
  }]
}
```

***

## 5. 总结：Manifest 与交互 JSON 的对应关系

| **Manifest 中的字段**     | **在交互 JSON 中的作用**                                     |
| ------------------------- | ------------------------------------------------------------ |
| `name` & `description`    | 注入到**第一次请求**的 `system` 消息中，辅助模型进行路由。   |
| `routing_config.triggers` | 用于在路由阶段给模型提供具体的关键词提示（Few-shot）。       |
| `instructions.md` (Path)  | 内容被读出后，注入到**第二次请求**的 `tool` 结果中。         |
| `required_tools`          | 决定了在后续交互中，`tools` 数组里该放入哪些具体的函数定义。 |

> **💡 小贴士**：
> 
> 别忘了在你的 Agent 后端设置一个 **Token 截断器**。当 `messages` 数组因为 SOP 注入而变得过长时，可以将最早的路由对话（第一次请求）进行摘要处理或删除，只保留当前的 Skill 执行逻辑。

