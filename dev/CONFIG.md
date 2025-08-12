# 配置文件

默认配置文件路径为：
- 当前目录下的 aipy.toml
- 用户主目录下的 .aipy.toml

配置文件包括三个部分的配置：
- 全局配置
- LLM 配置: [llm.{name}] 开始
- API 配置: [api.{name}] 开始

# 最小配置
aipy.toml:
```toml
[llm.trustoken]
api_key = "你的Trustoken API Key"
```

# LLM 配置
用于配置访问 LLM 的 API 信息。
格式和内容示例如下：
```toml
[llm.deepseek]
type = "deepseek"
model = "deepseek-chat"
api_key = "你的 DeepSeek API Key"
enable = true
default = false
timeout = 10
max_tokens = 8192
params = {}
```

其中：
- llm.deepseek: LLM 的名称为 `deepseek`，同一个配置文件里不可重名。
- type: LLM 的类型为 `deepseek`，支持的类型见后面列表。
- model: LLM 的模型名称。
- api_key: LLM 的 API Key。
- enable: 是否启用 LLM，默认为 `true`。
- default: 是否为默认 LLM，默认为 `false`。
- timeout: LLM 的请求超时时间，单位为秒，默认无超时。
- max_tokens: LLM 的最大 token 数，默认为 8192。
- tls_verify: true|false, 是否启用证书校验。这在某些环境中（特别是使用自签名证书或需要绕过SSL验证的场景）会很有用。

模型特有的配置参数，可以 params 配置指定。例如：
```toml
params = {thinking = {type = “enabled”, budget_tokens = 1024}}
```
注意：params 是 TOML 配置格式，不是 JSON，需要：
1. 用 = 代替 json 里的 :
2. 属性名不需要引号

LLM 类型列表
| 类型 | 描述 |
| --- | --- |
| trust | Trustoken API，model 默认为 `auto` |
| openai | OpenAI API，兼容 OpenAI 的 API |
| ollama | Ollama API |
| claude | Claude API |
| gemini | Gemini API |
| deepseek | DeepSeek API |
| grok | Grok API |
| azure | Azure API |
| oauth2 | OAuth2 Provider |
| doubao | DouBao |
| kimi | Kimi |
| bigmodel | bigmodel |
| z | z.ai |

# 显示配置
```toml
[display]
style = "classic"
theme = "default"
record = true
quiet = false
```

# 其它全局配置列表

| 配置 | 描述 |
| --- | --- |
| max_tokens | 全局最大 token 数 |
| max_rounds | 自动执行的最大轮数，默认 16 |
| lang | 默认语言，取值为 `en` 或 `zh` |
| workdir | 工作目录，默认为当前目录下的 `work` 子目录 |
| role | 角色，默认为 `aipy` |
