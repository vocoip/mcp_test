import yaml
import json
from fastapi import FastAPI, Body
from typing import Dict
from src.services.mcp_service import MCPService
from src.models.base import OpenAIModel, AnthropicModel, VolcEngineModel
from typing import List, Dict, Any
from pydantic import BaseModel

app = FastAPI()
mcp_service = MCPService()

def load_config():
    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f)

@app.on_event("startup")
async def startup_event():
    config = load_config()
    
    # 注册所有火山引擎模型
    for model_name, model_config in config.items():
        if model_name in ['dsr1', 'dsv3'] and isinstance(model_config, dict):
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

@app.post("/conversation")
async def conversation(request: ConversationRequest):
    result = await mcp_service.conversation(request.model_name, request.messages, request.show_reasoning)
    return result

# 添加流式对话接口
from fastapi.responses import StreamingResponse

@app.post("/conversation_stream")
async def conversation_stream(request: ConversationRequest):
    async def stream_generator():
        async for chunk in mcp_service.conversation_stream(request.model_name, request.messages, request.show_reasoning):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8088)  # 修改为8088端口，避免端口冲突