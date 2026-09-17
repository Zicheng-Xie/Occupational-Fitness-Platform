# Ollama 文本结构化与初始判断实验设计

## 目标和边界

第一阶段只解决以下链路：

```text
自由文本 .txt
  -> Ollama 按字段字典提出候选事实
  -> 本地确定性校验（原文、否定、主体、类型、范围、冲突）
  -> 与字段字典同名的结构化事实
  -> 确定性规则初判
  -> 对缺失、冲突、无法可靠映射或跨章节条件生成受约束的 RAG 请求
```

Ollama 不直接判定 Red Flag，也不修改规则结果。RAG 只接收规则生成的请求，不能补写患者事实或反向更改初始判断。

本文暂定 `schemas/field_dictionary.json` 为唯一字段字典。如果另有一个保存 dictionary 格式 TXT 的文件夹，需要在实施前给出目录位置和一份代表性样本。

## 当前实现基础

- `case_intake/traceable.py` 已能从部分固定英语表达和 `field = JSON` 附录提取事实。
- `llm.py` 已通过 Ollama `/api/chat` 和 JSON Schema 请求字段、值、原文引述。
- `case_intake/model_intake.py` 已检查字段、类型、范围、原文引述和少量字段语义。
- `rules/engine.py` 已使用三值逻辑处理已知、未知和冲突事实，并生成规则结果及 RAG 请求。
- `red_flag.py` 已把内部规则结果转换为公开的 `WorkflowRuleResult`。

主要缺口是字段字典缺少自然语言定义和提取约束、语义校验只覆盖少数字段、长文本没有分段与去重、现有抽取指标不能分别计算漏报和误报、模糊条件没有独立而明确的输出契约。

## 实验数据

建立独立的抽取实验集，不直接用规则期望充当抽取真值。

1. 保留现有 10 份护士记录作为兼容集。
2. 从五个模块各准备至少 20 份人工标注 TXT，共至少 100 份。
3. 每个模块覆盖肯定、明确否定、未提及、家族史、历史事件、当前事件、冲突表达、缩写、拼写变化、阈值边界和跨句表达。
4. 将同一事实改写成模板句、自然临床句、简写句三种形式，用于测试措辞鲁棒性。
5. 预先固定开发集和测试集；测试集在模型、提示词和校验器确定前不参与调整。

每个样本的标注至少包含：

```json
{
  "case_id": "...",
  "expected_facts": {
    "dictionary.field": {
      "value": true,
      "quote": "原文中的连续片段"
    }
  },
  "expected_abstentions": ["不应自动填入的字段"],
  "expected_initial_route": "local_result | needs_more_information | rag_fusion",
  "expected_rag_rule_ids": []
}
```

## 对照组

在完全相同的测试集上比较：

1. 现有确定性提取器。
2. 现有确定性提取器加当前 `llama3:8b`。
3. 现有确定性提取器加 `qwen3:8b`。
4. 如果机器资源不足，再测试 `qwen3:4b`，但不预设它能达到验收门槛。

模型统一使用 temperature 0、固定 seed、相同字段字典和 JSON Schema。每份输入至少重复运行三次，检查输出稳定性。

## 指标和验收门槛

字段级指标必须分别报告，不只报告 accuracy：

- precision、recall、F1；
- Red Flag 相关必需字段的 recall；
- 明确否定准确率；
- 家族史或第三方信息误归于患者的比例；
- unknown 被错误填值的比例；
- 原文引述完全匹配率；
- 类型、单位和范围通过率；
- 同一输入三次运行的一致率；
- 初始 route 准确率；
- 应进入 RAG 的 rule ID precision/recall；
- 单例延迟和内存占用。

建议的工程验收门槛：Red Flag 必需字段 recall 不低于 0.98；自动接受字段 precision 不低于 0.98；否定和主体错误率低于 0.5%；结构化输出及原文引述有效率为 100%；任何未通过确定性校验的候选必须 abstain，不能进入规则。

这些门槛是工程目标，不代表临床验证。

## 预计代码修改

### 1. 丰富字段字典

扩展 `schemas/field_dictionary.json`，为每个字段增加 `description`、`examples`、`negative_examples`、`do_not_infer` 和必要的同义表达。类型、单位及枚举仍由规则生成或进行一致性校验，避免出现两套字段定义。

### 2. 提取请求按模块和文本片段执行

修改 `llm.py`：

- 按请求模块只发送相关字段；
- 对长 TXT 做有重叠的段落分块；
- 输出 `field`、`value`、`quote`，并增加可选的 `subject`、`temporality` 和 `certainty`；
- 合并重复候选，保留所有证据位置；
- 记录模型名、digest、提示版本、耗时和 token 数。

### 3. 通用确定性校验层

修改 `case_intake/model_intake.py`：

- 校验原文中每一次引述的位置，而不是只使用第一次出现位置；
- 校验患者主体、否定、时间和不确定性；
- 同一字段出现不一致值时保存为 `conflicting`；
- 无法验证语义时保存为 withheld/unknown；
- 只允许 dictionary 中的字段进入 `ClinicalCase.facts`。

### 4. 明确模糊条件到 RAG 的契约

规则仍只读取 dictionary 同名事实。给规则输出增加可审计的歧义原因，例如：

- `missing_fact`；
- `conflicting_fact`；
- `requires_confirmation`；
- `cross_chapter_condition`；
- `unsupported_free_text`。

修改 `schemas/red_flag_result.py`、`rules/engine.py` 和 `retrieval/workflow.py`，让 RAG 请求携带 `rule_id`、dictionary 字段名、状态、原文证据、`rag_query_key` 和限定的 source IDs。RAG 仍不能自行创建事实。

### 5. 独立实验命令

增加一个批量实验命令和结果文件，能够选择模型、固定数据集、重复次数，并输出字段混淆统计、路由统计、RAG 请求统计和逐例错误清单。扩展 `case_intake/evaluation.py`，避免当前只计算已标注字段 exact accuracy 而漏掉模型多提取造成的假阳性。

### 6. 测试

增加以下回归测试：否定、家族史、假设性文字、历史与当前状态、重复引述、冲突值、拼写变化、长文本分块、模型超时、非法 JSON、模型未安装、dictionary 未知字段、模糊条件 RAG 契约及 RAG 不修改初始结果。

## 本地软件和模型

当前环境中 `ollama` 命令不可用，需要先安装 Ollama 或把已安装程序加入 PATH。

第一轮建议下载：

```powershell
ollama pull qwen3:8b
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

`qwen3:8b` 约 5.2 GB，作为主要结构化抽取候选；`llama3.1:8b` 约 4.9 GB，作为对照；`nomic-embed-text` 只用于后续 Chroma RAG，不参与初始事实判断。现有配置中的 `llama3:8b` 可以保留作历史基线，但不应在没有对照实验的情况下直接定为最终模型。

如果内存或显存有限，先只下载 `qwen3:8b`，完成抽取实验后再决定是否需要第二个模型和 embedding 模型。

## 实施顺序

1. 确认唯一 dictionary 来源以及模糊条件 TXT 的实际格式。
2. 建立标注协议和最小测试集。
3. 扩展字段字典和提取输出契约。
4. 实现分块、合并和通用校验。
5. 实现明确的模糊条件 RAG 请求。
6. 运行模型对照实验并选择模型。
7. 固定模型 digest、提示版本和验收结果，再接入默认工作流。
