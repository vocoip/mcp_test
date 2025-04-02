from typing import List, Dict, Any
from abc import ABC, abstractmethod

class BaseModel(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config  # 直接使用传入的配置

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass

    @abstractmethod
    async def conversation(self, messages: List[Dict[str, str]]) -> str:
        pass
        
    async def conversation_with_reasoning(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """带有推理过程的对话方法，默认实现只返回普通对话结果"""
        result = await self.conversation(messages)
        return {"response": result}

class OpenAIModel(BaseModel):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        import openai
        openai.api_key = self.config.get("api_key")
        self.model = self.config.get("model_name", "gpt-3.5-turbo")

    async def generate(self, prompt: str) -> str:
        import openai
        response = await openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    async def conversation(self, messages: List[Dict[str, str]]) -> str:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.config.get('api_key')}",
                "Content-Type": "application/json"
            }
            # 确保消息是基本字典类型，可以被JSON序列化
            serializable_messages = [dict(msg) for msg in messages]
            data = {
                "model": self.model,
                "messages": serializable_messages,
                "max_tokens": 1000
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            raise Exception(f"VolcEngine API调用失败: {str(e)}")

class AnthropicModel(BaseModel):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        import anthropic
        self.client = anthropic.Client(api_key=self.config.get("api_key"))
        self.model = self.config.get("model_name", "claude-2")

    async def generate(self, prompt: str) -> str:
        response = self.client.completion(
            prompt=prompt,
            model=self.model,
            max_tokens_to_sample=1000
        )
        return response.completion
        
    async def conversation(self, messages: List[Dict[str, str]]) -> str:
        try:
            prompt = "\n\n".join([f"{m['role']}: {m['content']}" for m in messages])
            response = self.client.completion(
                prompt=prompt,
                model=self.model,
                max_tokens_to_sample=1000
            )
            return response.completion
        except Exception as e:
            raise Exception(f"Anthropic API调用失败: {str(e)}")

class VolcEngineModel(BaseModel):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        import os
        import openai
        self.client = openai.OpenAI(
            api_key=os.environ.get("ARK_API_KEY") or self._get_config("api_key"),
            base_url=self._get_config("base_url", "https://ark.cn-beijing.volces.com/api/v3")
        )
        self.model = self._get_config("model_name", "ep-20250217050306-c7sc5")

    def _get_config(self, key: str, default=None):
        """安全获取配置项"""
        if key not in self.config:
            if default is None:
                raise ValueError(f"Missing required config: {key}")
            return default
        return self.config[key]

    def _validate_url(self, url: str) -> str:
        """验证并标准化URL"""
        if not url:
            raise ValueError("base_url is required")
        return url.rstrip('/') if url.startswith(('http://', 'https://')) else f"https://{url}".rstrip('/')

    async def _make_request(self, endpoint: str, payload: Dict) -> Dict:
        """统一请求封装"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 验证请求URL和参数
        # 确保URL格式正确
        endpoint = endpoint.lstrip('/')
        request_url = f"{self.base_url}/{self.api_version}/{endpoint}"
        if not request_url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid request URL: {request_url}")
            
        try:
            async with self.httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    request_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
        except self.httpx.HTTPStatusError as e:
            error_detail = f"HTTP error {e.response.status_code}: {e.response.text}"
            full_error = f"API请求失败 - URL: {request_url}, {error_detail}"
            raise Exception(full_error)
        except Exception as e:
            raise Exception(f"API请求失败: {str(e)}")

    async def generate(self, prompt: str) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            raise Exception(f"VolcEngine生成失败: {str(e)}")

    async def conversation(self, messages: List[Dict[str, str]]) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return completion.choices[0].message.content
        except Exception as e:
            raise Exception(f"VolcEngine对话失败: {str(e)}")
            
    async def conversation_stream(self, messages: List[Dict[str, str]]):
        """流式对话方法，支持实时输出"""
        try:
            # 使用stream=True启用流式输出
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            
            # 逐块返回响应
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"VolcEngine流式对话失败: {str(e)}")
            
    async def conversation_with_reasoning(self, messages: List[Any]) -> Dict[str, Any]:
        """带有推理过程的对话方法，返回模型的推理过程和最终回答"""
        try:
            # 添加系统消息，要求模型展示推理过程
            system_message = {"role": "system", "content": "请先进行思考，分析问题并给出推理过程，然后再给出最终答案。格式为：\n\n思考：[你的分析和推理过程]\n\n回答：[你的最终答案]"}
            
            # 将Pydantic模型对象转换为字典
            dict_messages = []
            for msg in messages:
                # 检查是否为Pydantic模型对象
                if hasattr(msg, "model_dump"):
                    dict_messages.append(msg.model_dump())
                elif hasattr(msg, "dict"):
                    dict_messages.append(msg.dict())
                else:
                    # 已经是字典或其他格式
                    dict_messages.append(msg)
            
            # 检查是否已有系统消息
            has_system = any(msg.get("role", "") == "system" for msg in dict_messages if isinstance(msg, dict))
            
            # 构建新的消息列表
            if has_system:
                # 如果已有系统消息，修改它
                new_messages = []
                for msg in dict_messages:
                    if isinstance(msg, dict) and msg.get("role", "") == "system":
                        msg["content"] = system_message["content"]
                    new_messages.append(msg)
            else:
                # 如果没有系统消息，添加一个
                new_messages = [system_message] + dict_messages
            
            # 调用API（使用流式输出）
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=new_messages,
                stream=True  # 启用流式输出
            )
            
            # 处理流式响应
            full_response = ""
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
            
            # 解析响应，提取推理过程和最终答案
            reasoning = ""
            answer = full_response
            
            # 尝试分离思考和回答部分
            if "思考：" in full_response and "回答：" in full_response:
                parts = full_response.split("回答：")
                if len(parts) >= 2:
                    answer = parts[1].strip()
                    reasoning_part = parts[0]
                    if "思考：" in reasoning_part:
                        reasoning = reasoning_part.split("思考：")[1].strip()
            
            return {"response": answer, "reasoning": reasoning}
        except Exception as e:
            raise Exception(f"VolcEngine推理对话失败: {str(e)}")