# MCP (Model Control Panel) 服务

MCP 是一个用于统一管理和调用多个大语言模型的服务平台。它提供了简单的 REST API 接口和Web UI界面，支持同时调用多个模型，便于进行模型响应的对比和管理。

## 项目特点

- 统一的模型调用接口：通过REST API和Web UI两种方式访问
- 多模型支持：可同时接入和管理多个大语言模型
- 灵活的配置：支持通过YAML配置文件管理模型参数
- 实时响应：支持SSE（Server-Sent Events）实现流式响应
- 错误处理：完善的错误处理机制，提供清晰的错误信息
- 可扩展性：模块化设计，易于添加新的模型支持

## 环境要求

- Python 3.8+
- 依赖包：
  - FastAPI：Web框架
  - Uvicorn：ASGI服务器
  - PyYAML：配置文件解析
  - python-dotenv：环境变量管理
  - openai：OpenAI API客户端
  - anthropic：Anthropic API客户端
  - sseclient-py：SSE客户端支持
  - aiohttp：异步HTTP客户端

## 项目结构

```
mcp/
├── config/             # 配置文件目录
│   └── config.yaml    # 模型配置文件
├── src/               # 源代码目录
│   ├── main.py       # 主程序入口
│   ├── mcp_client.py # MCP客户端实现
│   ├── client_ui.py  # Web UI实现
│   ├── models/       # 模型相关代码
│   ├── services/     # 服务层代码
│   └── tests/        # 测试代码
└── requirements.txt   # 项目依赖
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置模型参数

编辑 `config/config.yaml` 文件，填入相应的 API 密钥和模型参数：

```yaml
dsr1:
  api_key: "your-api-key"
  base_url: "https://ark.cn-beijing.volces.com/api/v3"
  model_name: "ep-20250217050306-c7sc5"

dsv3:
  api_key: "your-api-key"
  base_url: "https://ark.cn-beijing.volces.com/api/v3"
  model_name: "ep-20250401222444-k69nl"
```

### 3. 启动服务

```bash
python src/main.py
```

服务将在 http://127.0.0.1:8088 启动

## API 接口

### 1. 获取可用模型列表

```bash
GET /models
```

响应示例：
```json
{
    "models": ["dsr1", "dsv3"]
}
```

### 2. 使用指定模型生成文本

```bash
POST /generate/{model_name}
Content-Type: application/json

{
    "prompt": "你的提示文本",
    "stream": true  // 可选，是否使用流式响应
}
```

### 3. 使用所有模型生成文本

```bash
POST /generate_all
Content-Type: application/json

{
    "prompt": "你的提示文本",
    "stream": true  // 可选，是否使用流式响应
}
```

### 4. 进行对话

```bash
POST /conversation
Content-Type: application/json

{
    "model_name": "dsr1",
    "messages": [
        {
            "role": "user",
            "content": "你好"
        }
    ],
    "stream": true  // 可选，是否使用流式响应
}
```

## Web UI 使用说明

1. 访问 http://127.0.0.1:8088 打开Web界面
2. 在输入框中输入提示文本
3. 选择要使用的模型（可多选）
4. 点击"生成"按钮开始生成
5. 实时查看各个模型的响应结果

## 错误处理

服务会返回标准的HTTP状态码和详细的错误信息：

- 400：请求参数错误
- 401：认证失败
- 404：模型不存在
- 500：服务器内部错误

错误响应示例：
```json
{
    "error": {
        "code": "model_not_found",
        "message": "指定的模型不存在",
        "details": "请检查模型名称是否正确"
    }
}
```

## 开发指南

### 添加新模型支持

1. 在 `src/models` 目录下创建新的模型实现类
2. 在 `config/config.yaml` 中添加新模型的配置
3. 在 `src/main.py` 中注册新模型的路由

### 运行测试

```bash
python -m pytest src/tests
```

## 注意事项

1. 请妥善保管API密钥，不要将其提交到代码仓库
2. 建议在生产环境中使用环境变量管理敏感信息
3. 使用流式响应时，注意处理连接中断的情况
4. 建议对API调用进行速率限制，避免超出模型服务商的限制

## 常见问题

1. Q: 如何修改服务端口？
   A: 在启动命令中添加 `--port` 参数，例如：`python src/main.py --port 8089`

2. Q: 支持哪些模型服务商？
   A: 目前支持火山引擎的DSR1和DSV3模型，后续会添加更多支持

3. Q: 如何处理API调用超时？
   A: 服务默认超时时间为30秒，可以在配置文件中调整

## 更新日志

### v1.0.0 (2024-04-04)
- 初始版本发布
- 支持DSR1和DSV3模型
- 提供REST API和Web UI接口
- 支持流式响应