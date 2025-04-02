# MCP (Model Control Panel) 服务

MCP 是一个用于统一管理和调用多个大语言模型的服务平台。它提供了简单的 REST API 接口，支持同时调用多个模型，便于进行模型响应的对比和管理。

## 环境要求

- Python 3.8+
- 依赖包：
  - FastAPI
  - Uvicorn
  - PyYAML
  - python-dotenv

## 功能特点

- 支持多个大语言模型的统一接入
- 提供 RESTful API 接口
- 支持单独调用指定模型或同时调用所有已注册模型
- 模块化设计，易于扩展新的模型支持
- 统一的配置管理

## 支持的模型

目前支持以下模型：
- 火山引擎 DSR1 模型
- 火山引擎 DSV3 模型

## 配置说明

在 `config/config.yaml` 文件中配置模型参数：

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

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置模型参数

编辑 `config/config.yaml` 文件，填入相应的 API 密钥和模型参数。

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

### 2. 使用指定模型生成文本

```bash
POST /generate/{model_name}
Content-Type: application/json

{
    "prompt": "你的提示文本"
}
```

### 3. 使用所有模型生成文本

```bash
POST /generate_all
Content-Type: application/json

{
    "prompt": "你的提示文本"
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
    ]
}
```