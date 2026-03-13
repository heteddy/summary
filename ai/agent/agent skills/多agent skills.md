# 多个agent skills如何选择

当系统中存在多个 Agent Skills 时，处理的核心机制叫做 **“路由 (Routing)”** 或 **“调度 (Orchestration)”**。

如果不加控制地把所有技能 SOP 都塞进 System Prompt，会导致：

1. **Token 浪费**：上下文太长，费用变高。
2. **模型迷失**：指令太多，AI 容易“顾此失彼”，甚至产生幻觉。

以下是实现自动选择的成熟方案及 System Prompt 写法：

## 1. 自动选择的机制：路由模式 (Router Pattern)

通常采用 **“两阶段加载”** 策略：

- **第一阶段（感知与筛选）：** Agent 只加载一个包含所有技能 **简介（Manifest）** 的精简列表。
- **第二阶段（激活与执行）：** 当 AI 确定要用某个技能时，Agent 再动态地把该技能的 **详细 SOP** 加载到上下文中。

## 2. System Prompt 应该怎么写？

这个 Prompt 的目标是让 AI 扮演一个“调度员”。

```markdown
## Role
你是一个智能任务调度中心。你拥有以下专业技能库（Skills Library）：

## Skills Library
1. [Secret-Refactor]: 用于处理代码中的硬编码密钥、敏感信息迁移至环境变量。
2. [Test-Gen]: 用于为现有的 Python 函数生成单元测试用例。
3. [Doc-Expert]: 用于根据代码逻辑自动生成 README 或 API 文档。

## Workflow Rules
1. 识别：分析用户需求，判断是否属于上述任一技能范畴。
2. 激活：如果匹配，请通过调用 `select_skill(skill_name)` 工具来激活。
3. 组合：如果需求复杂，可以按顺序激活多个技能。
4. 兜底：如果不匹配任何技能，请使用通用助手能力回答。

## Constraints
- 除非激活技能，否则不要执行具体的重构或文档编写动作。
- 每次只展示当前激活技能所需的逻辑，保持上下文简洁。
```

# 示例：多技能调度交互 JSON 结构示例

这里展示了从“用户提问”到“技能切换”的完整数据流。  
场景：用户说 “帮我把这个文件的密钥改了，顺便写个说明文档。”

```markdown
# Role
你是一个智能任务调度中心（Agent Router）。你的职责是分析用户需求，并从下方的【技能库】中选择最合适的技能进行激活。

# Skills Library
1. [Secret-Refactor]: 
   - 触发场景：用户提到“密钥泄露”、“硬编码 API Key”、“改用环境变量”、“安全重构”。
   - 核心能力：自动扫描并迁移敏感信息。
2. [Test-Gen]: 
   - 触发场景：用户提到“写测试”、“单元测试”、“Pytest”、“覆盖率”。
   - 核心能力：为现有函数生成高质量测试代码。
3. [Doc-Expert]: 
   - 触发场景：用户提到“写文档”、“README”、“API 注释”、“项目说明”。
   - 核心能力：根据代码逻辑生成技术文档。

# Available Tools
- `activate_skill(skill_id: string)`: 激活指定技能，获取其详细操作指南。

# Workflow Rules
1. 仔细阅读用户请求。
2. 如果请求匹配【技能库】中的某项，必须首先调用 `activate_skill` 工具。
3. 如果用户请求模糊，请追问，不要随意猜测。
4. 在技能激活前，不要输出任何具体的代码重构或文档建议。
```

***

## 第一次交互 路由选择

### User->Agent 用户 -> Agent 的输入 (API Request)

这是用户通过前端（如网页或 IDE 插件）发送给 Agent 后端的数据。

```json
{
  "user_id": "dev_user_123",
  "session_id": "sess_abc_456",
  "message": "帮我把 app.py 里的 API Key 改成环境变量，现在这样直接写在代码里太不安全了。"
}
```

### Agent->LLM

Agent 接收到用户消息后，并不会直接转发，而是会封装上下文。它会将“调度指令（Router Prompt）”和“工具定义（Tool Definitions）”打包。

```json
{
  "model": "gemini-2.0-flash",
  "messages": [
    {
      "role": "system",
      "content": "你是一个智能任务调度中心。你的职责是分析用户需求，并从下方的【技能库】中选择最合适的技能进行激活。\n\n# 技能库\n1. [Secret-Refactor]: 用于处理代码中的硬编码密钥、敏感信息迁移至环境变量。核心能力：自动扫描并迁移敏感信息。\n2. [Test-Gen]: 用于为现有的 Python 函数生成单元测试用例。\n3. [Doc-Expert]: 用于根据代码逻辑自动生成 README 或 API 文档。\n\n# 约束\n- 必须先调用 activate_skill 激活技能，严禁在未激活前直接修改文件。\n- 如果用户需求不明确，请进行追问。"
    },
    {
      "role": "user",
      "content": "帮我把 app.py 里的 API Key 改成环境变量，现在这样直接写在代码里太不安全了。"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "activate_skill",
        "description": "根据技能 ID 激活特定的专业 Agent 技能",
        "parameters": {
          "type": "object",
          "properties": {
            "skill_id": {
              "type": "string",
              "enum": ["Secret-Refactor", "Test-Gen", "Doc-Expert"],
              "description": "要激活的技能唯一标识符"
            },
            "reason": {
              "type": "string",
              "description": "选择该技能的原因简述"
            }
          },
          "required": ["skill_id"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

### LLM 返回给 Agent 的响应 (JSON):

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "tool_calls": [
          {
            "id": "call_refactor_001",
            "type": "function",
            "function": {
              "name": "activate_skill",
              "arguments": "{\"skill_id\": \"Secret-Refactor\", \"reason\": \"User wants to move hardcoded API keys to environment variables for security.\"}"
            }
          }
        ]
      }
    }
  ]
}
```

***

## 第二步 技能注入与初步规划 (Action Planning)

解析这个 JSON。 当 Agent 后端检测到第一次请求输出的是 activate_skill("Secret-Refactor") 后，它会执行以下逻辑：  
从服务器磁盘读取 /skills/Secret-Refactor/instructions.md。  
将该文件内容作为 Tool Output 返回给模型，并要求模型开始执行。

### 2.1  agent->llm

<b><span style="color:rgba(244,63,94,1)">注意：以为是发送如下请求：</span></b>

```json
{
  "model": "gemini-2.0-flash",
  "messages": [
    {
      "role": "system",
      "content": "你是一个智能任务调度中心...（保留之前的调度协议内容）"
    },
    {
      "role": "user",
      "content": "帮我把 app.py 里的 API Key 改成环境变量，现在这样直接写在代码里太不安全了。"
    },
    {
      "role": "assistant",
      "tool_calls": [
        {
          "id": "call_act_999",
          "type": "function",
          "function": {
            "name": "activate_skill",
            "arguments": "{\"skill_id\": \"Secret-Refactor\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_act_999",
      "content": "【技能：Secret-Refactor 已激活】\n操作规范：\n1. 首先必须调用 read_file 查看文件内容。\n2. 检查是否存在 'import os'，若无则必须在首行添加。\n3. 使用 os.getenv('VARIABLE_NAME') 替换硬编码字符串。\n4. 必须创建一个 .env.example 模板文件，内容格式为 VARIABLE_NAME=your_value_here。"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "read_file",
        "parameters": { "type": "object", "properties": { "path": { "type": "string" } } }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "write_file",
        "parameters": { "type": "object", "properties": { "path": { "type": "string" }, "content": { "type": "string" } } }
      }
    }
  ]
}
```

<b><span style="color:rgba(244,63,94,1)">实际发送的请求为 </span></b>

这里体现了分层的思想

```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "system", 
      "content": "你现在已激活 [secret-refactor] 技能。请严格遵守以下 SOP：\n1. 使用 read_file 读取源码。\n2. 必须检查首行是否有 'import os'，缺失则补上。\n3. 替换硬编码字符串为 os.getenv()。\n4. 必须创建 .env.example 文件。" 
    },
    { "role": "user", "content": "帮我把 app.py 里的 API Key 改成环境变量..." },
    { "role": "assistant", "tool_calls": [{ "id": "call_route_01", "function": { "name": "activate_skill", "arguments": "..." } }] },
    { "role": "tool", "tool_call_id": "call_route_01", "content": "Success: secret-refactor skill loaded." }
  ],
  "tools": [
    { "type": "function", "function": { "name": "read_file", "parameters": { "type": "object", "properties": { "path": { "type": "string" } } } } }
  ]
}
```



### 2.2 LLM返回给 Agent (Response JSON)

模型阅读了技能规范，意识到不能直接“猜”代码，必须先“看”代码。

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "好的，我已经激活了安全重构技能。首先我需要读取 app.py 来定位硬编码的密钥。",
        "tool_calls": [
          {
            "id": "call_read_001",
            "type": "function",
            "function": {
              "name": "read_file",
              "arguments": "{\"path\": \"app.py\"}"
            }
          }
        ]
      }
    }
  ]
}
```

***

## 第三次交互：环境感知 (Context Observation)

Agent 执行 read_file（可能通过 MCP Server 访问文件系统），并将结果返回。

### 3.1 agent->llm

```json
{
  "model": "gemini-2.0-flash",
  "messages": [
    "...(省略之前的对话上下文)...",
    {
      "role": "assistant",
      "tool_calls": [{"id": "call_read_001", "function": {"name": "read_file", "arguments": "{\"path\": \"app.py\"}"}}]
    },
    {
      "role": "tool",
      "tool_call_id": "call_read_001",
      "content": "API_KEY = \"sk-key123456789\"\n\ndef start_app():\n    print(f\"Using {API_KEY}\")"
    }
  ]
}
```

### 3.2 llm->agent

```json5
{
    "id": "chatcmpl-def-789",
    "model": "gemini-2.0-flash",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "我已经分析了 app.py 的内容，发现了硬编码的 API_KEY。根据安全重构规范，我将执行以下操作：\n1. 在 app.py 中导入 os 模块并将密钥替换为环境变量读取方式。\n2. 创建一个 .env.example 文件供参考。",
                "tool_calls": [
                    {
                        "id": "call_write_001",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": "{\"path\": \"app.py\", \"content\": \"import os\\n\\nAPI_KEY = os.getenv('API_KEY')\\n\\ndef start_app():\\n    print(f'Using {API_KEY}')\"}"
                        }
                    },
                    {
                        "id": "call_write_002",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": "{\"path\": \".env.example\", \"content\": \"API_KEY=your_api_key_here\"}"
                        }
                    }
                ]
            },
            "finish_reason": "tool_calls"
        }
    ]
}
```

***

## 第四次交互：最终执行

此时模型结合了 Skill 规范（必须导入 os，必须创建模板文件）和 真实代码，做出最终决策。

4.1  agent ->llm  

todo

<span style="color:rgba(244,63,94,1)"> <font color="red">上下文错误</font></span>

```json
{
  "model": "gemini-2.0-flash",
  "messages": [
    { "role": "system", "content": "你是一个智能任务调度中心...（调度协议内容）" },
    { "role": "user", "content": "帮我把 app.py 里的 API Key 改成环境变量..." },
    {
      "role": "assistant",
      "tool_calls": [{ "id": "call_act_999", "function": { "name": "activate_skill", "arguments": "{\"skill_id\": \"Secret-Refactor\"}" } }]
    },
    { "role": "tool", "tool_call_id": "call_act_999", "content": "【技能：Secret-Refactor 已激活】操作规范：1.必须read_file...2.导入os...3.创建.env.example..." },
    {
      "role": "assistant",
      "tool_calls": [{ "id": "call_read_001", "function": { "name": "read_file", "arguments": "{\"path\": \"app.py\"}" } }]
    },
    { "role": "tool", "tool_call_id": "call_read_001", "content": "API_KEY = \"sk-key123456789\"\ndef start_app():..." },
    {
      "role": "assistant",
      "tool_calls": [
        { "id": "call_write_001", "function": { "name": "write_file", "arguments": "{\"path\": \"app.py\", \"content\": \"...代码内容...\"}" } },
        { "id": "call_write_002", "function": { "name": "write_file", "arguments": "{\"path\": \".env.example\", \"content\": \"API_KEY=your_key_here\"}" } }
      ]
    },
    /* --- 以下是第四次请求新增的内容：执行结果反馈 --- */
    {
      "role": "tool",
      "tool_call_id": "call_write_001",
      "content": "{\"status\": \"success\", \"message\": \"app.py has been updated successfully.\"}"
    },
    {
      "role": "tool",
      "tool_call_id": "call_write_002",
      "content": "{\"status\": \"success\", \"message\": \".env.example has been created successfully.\"}"
    }
  ],
  "tools": [ /* 依然携带可用工具列表，防止模型需要后续操作 */ ]
}
```

4.2. llm->Agent (Response JSON) 注意：模型在这一次响应中同时调用了两个工具。

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "我已经找到了硬编码的密钥。现在我将：\n1. 修改 app.py 以导入 os 并使用环境变量。\n2. 创建 .env.example 文件。",
        "tool_calls": [
          {
            "id": "call_write_001",
            "type": "function",
            "function": {
              "name": "write_file",
              "arguments": "{\"path\": \"app.py\", \"content\": \"import os\\n\\nAPI_KEY = os.getenv('API_KEY')\\n\\ndef start_app():\\n    print(f'Using {API_KEY}')\"}"
            }
          },
          {
            "id": "call_write_002",
            "type": "function",
            "function": {
              "name": "write_file",
              "arguments": "{\"path\": \".env.example\", \"content\": \"API_KEY=your_api_key_here\"}"
            }
          }
        ]
      }
    }
  ]
}
```

# 核心总结：为什么流程要这么设计？

## Context Management (上下文管理)：

在第一次请求时，我们只发送了技能列表（非常短）。  
只有在确认要用 Secret-Refactor 时，才在第二次请求的 tool 结果中塞入几百行的 SOP。这极大地节省了 Token。

## Explicit Guidance (显性引导)：

通过 role: tool 返回的 SOP 是“新鲜”的。模型在推理时会给予这些最新注入的规则更高的权重（Attention Weight）。

## Atomicity (原子性)

你可以看到，最后一步模型同时输出了两个 write_file。这是因为 Skill 指南里写了“必须同步创建模板文件”，模型被技能逻辑约束，实现了复杂任务的同步处理。



### 进阶：如何防止 AI “乱选”？

在 `definition.json` 中为每个技能添加 **"Trigger Examples" (触发示例)**：

```json
{
  "name": "Secret-Refactor",
  "triggers": [
    "API_KEY is leaked",
    "hardcoded password",
    "move secrets to .env"
  ]
}
```

将这些 triggers 加入路由 Prompt，能显著提高 AI 选择的准确率。

## `manifest.json` 结构设计

为了防止误选，`manifest.json` 不仅要告诉 AI “我是做什么的”，还要告诉它“**我不能做什么**”。

```json
{
    "skills": [
        {
            "id": "legal-expert-v1",
            "name": "法务合规助手",
            "version": "1.0.2",
            "description": "专门处理合同审查、劳动法咨询及隐私协议合规性。适用于法律条文检索和风险点提示。",
            "routing_config": {
                "triggers": [
                    "合同条款",
                    "违约责任",
                    "劳动仲裁",
                    "合规审查",
                    "法律风险"
                ],
                "negative_triggers": [
                    "代码纠错",
                    "财务报表审计",
                    "发票报销"
                ],
                "examples": [
                    {
                        "user_input": "这份供应商合同有法律风险吗？",
                        "reason": "涉及合同与风险识别"
                    },
                    {
                        "user_input": "程序员加班费怎么算？",
                        "reason": "涉及劳动法咨询"
                    }
                ]
            },
            "constraints": "严禁提供具体的起草服务，仅限审查和建议。不具备财务税务计算能力。"
        },
        {
            "id": "tech-refactor-v2",
            "name": "技术架构重构",
            "description": "处理代码重构、性能优化及系统架构设计建议。",
            "routing_config": {
                "triggers": [
                    "代码重构",
                    "优化性能",
                    "API设计",
                    "数据库迁移"
                ],
                "negative_triggers": [
                    "法律条文",
                    "税务筹划"
                ],
                "examples": [
                    {
                        "user_input": "如何优化这个 SQL 的执行效率？",
                        "reason": "涉及数据库性能"
                    }
                ]
            }
        }
    ]
}
```

