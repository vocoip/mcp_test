import yaml
import json
import sys
import os
from fastapi import FastAPI, Body
from typing import Dict

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.mcp_service import MCPService
from src.models.base import OpenAIModel, AnthropicModel, VolcEngineModel
from src.models.deepseek_model import DeepSeekModel
from typing import List, Dict, Any
from pydantic import BaseModel

app = FastAPI()
mcp_service = MCPService()

def load_config():
    with open("config/config.yaml", "r", encoding='utf-8') as f:
        return yaml.safe_load(f)

@app.on_event("startup")
async def startup_event():
    config = load_config()
    
    # 注册所有模型
    for model_name, model_config in config.items():
        if model_name in ['dsr1', 'dsv3'] and isinstance(model_config, dict):
            # 注册DeepSeek模型 - 创建一个专门的DeepSeekModel类实例
            # 确保base_url正确设置为DeepSeek API的URL
            if 'base_url' not in model_config or 'deepseek.com' not in model_config['base_url']:
                print(f"警告: DeepSeek模型 {model_name} 的base_url配置可能不正确")
            
            # 确保模型名称正确 - DeepSeek API使用deepseek-chat作为模型名称
            if 'model_name' not in model_config:
                model_config['model_name'] = 'deepseek-chat'
            
            # 使用专门的DeepSeekModel类处理DeepSeek API
            mcp_service.register_model(
                model_name,
                DeepSeekModel(model_config)
            )
        elif model_name in ['vdsr1', 'vdsv3'] and isinstance(model_config, dict):
            # 注册火山引擎模型
            mcp_service.register_model(
                model_name,
                VolcEngineModel(model_config)
            )

@app.get("/models")
async def list_models():
    return {"models": list(mcp_service.models.keys())}

@app.post("/generate/{model_name}")
async def generate(model_name: str, prompt: str = Body(..., embed=True)):
    return {"response": await mcp_service.generate(model_name, prompt)}

@app.post("/generate_all")
async def generate_all(prompt: str):
    return await mcp_service.generate_all(prompt)

class Message(BaseModel):
    role: str  # "user" 或 "assistant"
    content: str

class ConversationRequest(BaseModel):
    messages: List[Message]
    model_name: str
    show_reasoning: bool = False
    char_by_char: bool = True  # 默认启用逐字符输出

@app.post("/conversation")
async def conversation(request: ConversationRequest):
    result = await mcp_service.conversation(request.model_name, request.messages, request.show_reasoning)
    return result

# 添加流式对话接口
from fastapi.responses import StreamingResponse

@app.post("/conversation_stream")
async def conversation_stream(request: ConversationRequest):
    async def stream_generator():
        # 传递char_by_char参数，支持逐字符输出
        char_by_char = getattr(request, 'char_by_char', True)  # 默认启用逐字符输出
        async for chunk in mcp_service.conversation_stream(request.model_name, request.messages, request.show_reasoning, char_by_char):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8088)  # 修改为8088端口，避免端口冲突