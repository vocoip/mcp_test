from typing import List, Dict, Any
import openai
import httpx
from .base import BaseModel

class DeepSeekModel(BaseModel):
    """
    专门用于处理DeepSeek API的模型类
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        import os
        
        # 设置基本参数
        # DeepSeek API的正确格式应该是 https://api.deepseek.com/v1/chat/completions
        # 因此base_url应该只包含域名部分，不包含路径
        original_base_url = self._get_config("base_url", "https://api.deepseek.com")
        # 去除可能的路径部分，只保留域名
        self.base_url = original_base_url.split("/v")[0] if "/v" in original_base_url else original_base_url
        # 确保base_url不以/结尾
        self.base_url = self.base_url.rstrip("/")
        
        self.api_key = os.environ.get("DEEPSEEK_API_KEY") or self._get_config("api_key")
        self.httpx = httpx
        self.timeout = 30.0
        
        # 初始化OpenAI客户端，使用正确的API路径
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=f"{self.base_url}/v1"
        )
        
        # 设置模型名称
        self.model = self._get_config("model_name")
        # 确保模型名称正确
        if not self.model.startswith("deepseek-"):
            # 根据配置自动调整模型名称
            if "v3" in original_base_url or "v3" in self._get_config("model_name", ""):
                self.model = "deepseek-chat"
            elif "r1" in original_base_url or "r1" in self._get_config("model_name", ""):
                self.model = "deepseek-chat"
            else:
                # 默认使用deepseek-chat
                self.model = "deepseek-chat"

    def _get_config(self, key: str, default=None):
        """安全获取配置项"""
        if key not in self.config:
            if default is None:
                raise ValueError(f"Missing required config: {key}")
            return default
        return self.config[key]

    async def generate(self, prompt: str) -> str:
        """生成文本"""
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            error_msg = f"DeepSeek生成失败: {str(e)}"
            raise Exception(error_msg)

    async def conversation(self, messages: List[Dict[str, str]], show_reasoning: bool = False) -> str:
        """对话接口"""
        try:
            if show_reasoning:
                # 如果需要显示推理过程，调用带有推理的方法
                # 这里直接返回字典格式，包含推理过程和最终答案
                # MCPService会处理这个字典格式的返回值
                return await self.conversation_with_reasoning(messages)
            else:
                # 普通对话模式
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
                return completion.choices[0].message.content
        except Exception as e:
            error_msg = f"DeepSeek API调用失败: {str(e)}"
            raise Exception(error_msg)
            
    async def conversation_stream(self, messages: List[Dict[str, str]]):
        """流式对话方法，支持实时输出"""
        try:
            # 使用stream=True启用流式输出
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            
            # 逐字符返回响应，确保每个字符都能立即传输
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    # 即使是空字符串也要返回，确保前端能接收到所有字符
                    yield chunk.choices[0].delta.content
        except Exception as e:
            error_msg = f"DeepSeek API流式调用失败: {str(e)}"
            raise Exception(error_msg)
            
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
            raise Exception(f"DeepSeek推理对话失败: {str(e)}")