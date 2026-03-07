## 什么是 MCP？ 

MCP（模型上下文协议）是一个使大型语言模型（LLMs，如 Claude）能够与外部工具和数据源交互的协议。使用 MCP可以：

- 构建为 LLMs 提供工具和数据的服务器
- 将这些服务器连接到兼容 MCP 的客户端
- 通过自定义功能扩展 LLM 的能力

## 核心概念 

MCP 服务器可以提供三种主要类型的功能：

1. **工具**：可被 LLM 调用的函数（需要用户批准）
2. **资源**：可被客户端读取的类文件数据（如 API 响应或文件内容）
3. **提示词**：帮助用户完成特定任务的预设模板

# 使用

1. 支持

# 例子

在使用 Model Context Protocol (MCP) 的场景下，DeepSeek（或其他大模型）作为“大脑”，通过宿主程序（Host，如 Claude Desktop 或 IDE）与 MCP 服务器提供的计算器工具进行交互。

以下是实现 `a + b` 计算的完整调用流程分析。

***

### 1. 初始阶段：告知模型有哪些工具

当用户输入“帮我计算 15 加 27”时，宿主程序会将用户指令和 MCP 服务器提供的 **工具定义 (Tool Definitions)** 一并发送给 DeepSeek。

#### **请求结构 (Host -> DeepSeek)**

```json
{
  "model": "deepseek-chat",
  "messages": [
    { "role": "user", "content": "帮我计算 15 加 27" }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "calculator_add",
        "description": "执行加法运算",
        "parameters": {
          "type": "object",
          "properties": {
            "a": { "type": "number", "description": "第一个数字" },
            "b": { "type": "number", "description": "第二个数字" }
          },
          "required": ["a", "b"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

**参数解释：**

- **`tools`** **tools**: 模型可用的工具列表。
- **`name`** **name**: MCP 工具的唯一标识符。
- **`description`** **description**: 极其重要，模型靠它理解何时该用这个工具。
- **`parameters`** **parameters**: 定义了调用工具时必须提供的输入格式（JSON Schema）。

***

### 2. 模型决策阶段：模型决定调用工具

DeepSeek 分析需求后，意识到自己不能直接“硬算”（为了准确性），于是决定调用 `calculator_add`。

#### **响应结构 (DeepSeek -> Host)**

```json
{
  "id": "chatcmpl-123",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "calculator_add",
              "arguments": "{\"a\": 15, \"b\": 27}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

**参数解释：**

- **`tool_calls`** **tool_calls**: 数组形式，表示模型想要执行的一个或多个动作。
- **`id`** **id**: 此次工具调用的唯一 ID，后续回传结果时必须携带，用于匹配。
- **`arguments`** **arguments**: 模型根据用户输入提取并生成的参数字符串。
- **`finish_reason: "tool_calls"`** **finish_reason: "tool_calls"**: 告知宿主程序，对话未结束，我正在等待工具执行结果。

***

### 3. 执行阶段：宿主调用 MCP Server

此时，宿主程序（Host）解析上述 JSON，本地调用 MCP 计算器服务器，得到结果 `42`。

***

### 4. 结果回传阶段：将计算结果交给模型

宿主程序将工具的执行结果打包，再次发送给 DeepSeek。

#### **请求结构 (Host -> DeepSeek)**

JSON

````
{
  "model": "deepseek-chat",
  "messages": [
    { "role": "user", "content": "帮我计算 15 加 27" },
    { 
      "role": "assistant", 
      "tool_calls": [ { "id": "call_abc123", "type": "function", "function": { "name": "calculator_add", "arguments": "{\"a\": 15, \"b\": 27}" } } ] 
    },
    {
      "role": "tool",
      "tool_call_id": "call_abc123",
      "content": "42"
    }
  ]
}
````

**参数解释：**

- **`role: "tool"`** **role: "tool"**: 一个特殊的角色，表示这条消息是外部工具的输出。
- **`tool_call_id`** **tool_call_id**: 必须与步骤 2 中的 ID 一致，否则模型会“断片”。
- **`content`** **content**: 工具返回的真实数据。

***

### 5. 最终生成阶段：模型给出自然语言回答

DeepSeek 拿到 `42` 后，结合上下文组织语言。

#### **最终响应结构 (DeepSeek -> Host)**



```JSON
{
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "计算好了，15 加 27 的结果是 42。"
      },
      "finish_reason": "stop"
    }
  ]
}
```

***

### 总结

MCP 调用过程本质上是一个 **“请求 -> 暂挂 -> 执行 -> 回传 -> 总结”** 的闭环。

| **步骤** | **关键参数**    | **作用**                             |
| -------- | --------------- | ------------------------------------ |
| **定义** | `tools`         | 告诉 DeepSeek “你会什么”             |
| **调用** | `tool_calls`    | DeepSeek 说 “我想用这个，参数是这个” |
| **关联** | `tool_call_id`  | 确保计算结果填回正确的“坑”里         |
| **完成** | `finish_reason` | 标志任务是继续执行还是已圆满结束     |

你想尝试编写一个自己的 MCP 服务器代码示例吗？或者想了解如何配置 DeepSeek 接入现有的 MCP 工具库？