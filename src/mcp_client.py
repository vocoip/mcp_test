import requests
from typing import Dict, Any, Generator, AsyncGenerator, List, Optional, Union
import json
import time
import asyncio
import aiohttp
from sseclient import SSEClient
import backoff
from aiohttp import ClientTimeout, ClientSession, ClientResponseError

class MCPClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8088", max_retries: int = 3, retry_delay: float = 0.5):
        self.base_url = base_url
        self.conversation_history = []  # 初始化对话历史记录
        self.headers = {"Content-Type": "application/json"}  # 添加headers初始化
        self.max_retries = max_retries  # 最大重试次数
        self.retry_delay = retry_delay  # 重试延迟时间(秒)
        self.timeout = ClientTimeout(total=60, connect=2)  # 设置默认超时时间
        self.model_providers = {
            "ep-": "VolcEngine",
            "vds": "VolcEngine",
            "deepseek": "DeepSeek",
            "ds": "DeepSeek",
            "dsr": "DeepSeek",  # 添加dsr前缀识别
            "dsv": "DeepSeek",  # 添加dsv前缀识别
            "gpt-": "OpenAI",
            "claude-": "Anthropic"
        }  # 支持更多模型提供商

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3, jitter=None)
    def _check_connection(self) -> bool:
        """检查服务是否可用（同步版本）"""
        try:
            response = requests.get(f"{self.base_url}/models", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
            
    async def _check_connection_async(self) -> bool:
        """检查服务是否可用（异步版本）"""
        try:
            async with ClientSession(timeout=ClientTimeout(total=2)) as session:
                async with session.get(f"{self.base_url}/models") as response:
                    return response.status == 200
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return False
    
    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def list_models(self) -> Dict[str, Any]:
        """获取所有可用模型列表（同步版本）"""
        url = f"{self.base_url}/models"
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"获取模型列表失败: {str(e)}")
            return {"models": [], "error": str(e)}
    
    async def list_models_async(self) -> Dict[str, Any]:
        """获取所有可用模型列表（异步版本）"""
        url = f"{self.base_url}/models"
        try:
            async with ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=self.headers) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            error_msg = f"获取模型列表失败: {str(e)}"
            return {"models": [], "error": error_msg}
    
    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def generate(self, model_name: str, prompt: str) -> Dict[str, Any]:
        """调用单个模型生成响应（同步版本）"""
        url = f"{self.base_url}/generate/{model_name}"
        
        # 检查模型名称，确保正确识别DeepSeek模型
        model_provider = None
        for prefix, provider in self.model_providers.items():
            if model_name.startswith(prefix):
                model_provider = provider
                break
                
        # 构造请求数据
        data = {"prompt": prompt}
        
        # 如果是DeepSeek模型，添加特殊处理
        if model_provider == "DeepSeek":
            data["provider"] = "deepseek"
            
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=data,
                timeout=10  # 设置合理的超时时间
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"请求错误: {e.response.text}")  # 打印详细错误信息
            return {"error": str(e)}
        except requests.exceptions.RequestException as e:
            return {"error": f"请求异常: {str(e)}"}
            
    async def generate_async(self, model_name: str, prompt: str) -> Dict[str, Any]:
        """调用单个模型生成响应（异步版本）"""
        url = f"{self.base_url}/generate/{model_name}"
        
        # 检查模型名称，确保正确识别DeepSeek模型
        model_provider = None
        for prefix, provider in self.model_providers.items():
            if model_name.startswith(prefix):
                model_provider = provider
                break
                
        # 构造请求数据
        data = {"prompt": prompt}
        
        # 如果是DeepSeek模型，添加特殊处理
        if model_provider == "DeepSeek":
            data["provider"] = "deepseek"
            
        try:
            async with ClientSession(timeout=self.timeout) as session:
                async with session.post(url, headers=self.headers, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientResponseError as e:
            return {"error": f"HTTP错误: {e.status} - {e.message}"}
        except aiohttp.ClientError as e:
            return {"error": f"请求异常: {str(e)}"}
    
    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def generate_all(self, prompt: str) -> Dict[str, Any]:
        """调用所有模型生成响应（同步版本）"""
        url = f"{self.base_url}/generate_all"
        
        # 构造请求数据
        data = {"prompt": prompt, "provider_info": True}
        
        try:
            response = requests.post(
                url, 
                json=data,
                headers=self.headers,
                timeout=15  # 设置较长的超时时间，因为需要调用多个模型
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"请求异常: {str(e)}"}
            
    async def generate_all_async(self, prompt: str) -> Dict[str, Any]:
        """调用所有模型生成响应（异步版本）"""
        url = f"{self.base_url}/generate_all"
        
        # 构造请求数据
        data = {"prompt": prompt, "provider_info": True}
        
        try:
            async with ClientSession(timeout=ClientTimeout(total=30)) as session:  # 设置更长的超时时间
                async with session.post(url, json=data, headers=self.headers) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientResponseError as e:
            return {"error": f"HTTP错误: {e.status} - {e.message}"}
        except aiohttp.ClientError as e:
            return {"error": f"请求异常: {str(e)}"}
        
    # 旧的list_models方法已被替换为带有重试机制的版本

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def conversation(self, model_name: str, message: str, show_reasoning: bool = False) -> Dict[str, Any]:
        """对话方法（同步版本）"""
        # 添加用户消息到历史
        self.conversation_history.append({"role": "user", "content": message})
        
        # 检查模型名称，确保正确识别DeepSeek模型
        model_provider = None
        for prefix, provider in self.model_providers.items():
            if model_name.startswith(prefix):
                model_provider = provider
                break
        
        # 构造请求数据
        data = {
            "model_name": model_name,
            "messages": self.conversation_history
        }
        
        # 如果是DeepSeek模型，添加特殊处理
        if model_provider == "DeepSeek":
            data["provider"] = "deepseek"
        
        # 如果需要显示推理过程，添加相应参数
        if show_reasoning:
            data["show_reasoning"] = True
        
        # 发送请求并记录耗时
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/conversation",
                json=data,
                headers=self.headers,
                timeout=15  # 设置合理的超时时间
            )
            response.raise_for_status()
            elapsed_time = time.time() - start_time
            
            # 处理响应
            response_data = response.json()
            assistant_message = response_data["response"]
            
            # 将助手消息添加到历史记录
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # 如果有推理过程，返回它
            if show_reasoning and "reasoning" in response_data:
                return {"response": assistant_message, "reasoning": response_data["reasoning"]}
            else:
                return {"response": assistant_message}
        except requests.exceptions.HTTPError as e:
            return {"error": f"HTTP错误: {e.response.status_code} - {e.response.text}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"请求异常: {str(e)}"}
            
    async def conversation_async(self, model_name: str, message: str, show_reasoning: bool = False) -> Dict[str, Any]:
        """对话方法（异步版本）"""
        # 添加用户消息到历史
        self.conversation_history.append({"role": "user", "content": message})
        
        # 检查模型名称，确保正确识别DeepSeek模型
        model_provider = None
        for prefix, provider in self.model_providers.items():
            if model_name.startswith(prefix):
                model_provider = provider
                break
        
        # 构造请求数据
        data = {
            "model_name": model_name,
            "messages": self.conversation_history,
            "show_reasoning": show_reasoning,
            "char_by_char": True  # 启用逐字输出模式
        }
        
        # 如果是DeepSeek模型，添加特殊处理
        if model_provider == "DeepSeek":
            data["provider"] = "deepseek"
        
        try:
            async with ClientSession(timeout=self.timeout) as session:
                start_time = time.time()
                async with session.post(f"{self.base_url}/conversation", json=data, headers=self.headers) as response:
                    response.raise_for_status()
                    response_data = await response.json()
                    
                    assistant_message = response_data["response"]
                    
                    # 将助手消息添加到历史记录
                    self.conversation_history.append({"role": "assistant", "content": assistant_message})
                    
                    # 如果有推理过程，返回它
                    if show_reasoning and "reasoning" in response_data:
                        return {"response": assistant_message, "reasoning": response_data["reasoning"]}
                    else:
                        return {"response": assistant_message}
        except aiohttp.ClientResponseError as e:
            return {"error": f"HTTP错误: {e.status} - {e.message}"}
        except aiohttp.ClientError as e:
            return {"error": f"请求异常: {str(e)}"}
            
    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=2)
    def conversation_stream(self, model_name: str, message: str, show_reasoning: bool = False) -> Generator[Dict[str, Any], None, None]:
        """流式对话方法，支持实时输出推理过程和回答（同步版本）"""
        # 添加用户消息到历史
        self.conversation_history.append({"role": "user", "content": message})
        
        # 检查模型名称，确保正确识别DeepSeek模型
        model_provider = None
        for prefix, provider in self.model_providers.items():
            if model_name.startswith(prefix):
                model_provider = provider
                break
        
        # 构造请求数据
        data = {
            "model_name": model_name,
            "messages": self.conversation_history,
            "show_reasoning": show_reasoning,
            "char_by_char": True  # 启用逐字输出模式
        }
        
        # 如果是DeepSeek模型，添加特殊处理
        if model_provider == "DeepSeek":
            data["provider"] = "deepseek"
        
        try:
            # 使用SSE客户端获取流式响应，设置更短的连接超时以提高响应速度
            response = requests.post(
                f"{self.base_url}/conversation_stream",
                json=data,
                headers=self.headers,
                stream=True,
                timeout=(0.3, 60.0)  # 连接超时0.3秒，读取超时60秒
            )
            
            if response.status_code == 200:
                # 初始化变量
                final_response = ""
                
                # 立即发送连接状态，让用户知道请求已发送
                yield {"status": "connected", "message": "已连接到服务器"}
                
                # 使用原始响应对象直接读取数据流，避免SSEClient可能的缓冲
                for line in response.iter_lines():
                    if not line:
                        continue
                        
                    # 解析SSE格式的数据行
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str:
                            try:
                                # 立即解析并处理数据，减少处理延迟
                                chunk_data = json.loads(data_str)
                                yield chunk_data
                                
                                # 保存最终响应用于历史记录
                                if "response" in chunk_data and chunk_data["response"] is not None:
                                    final_response = chunk_data["response"]
                            except json.JSONDecodeError:
                                yield {"error": "无法解析服务器响应"}
                
                # 将最终助手消息添加到历史记录
                if final_response:
                    self.conversation_history.append({"role": "assistant", "content": final_response})
                    
                # 发送完成状态
                yield {"status": "completed"}
            else:
                yield {"error": f"HTTP错误: {response.status_code} - {response.text}"}
        except requests.exceptions.Timeout:
            yield {"error": "连接超时，请检查服务器状态或网络连接"}
        except requests.exceptions.RequestException as e:
            yield {"error": f"请求异常: {str(e)}"}
        except Exception as e:
            yield {"error": f"未知错误: {str(e)}"}
            
    async def conversation_stream_async(self, model_name: str, message: str, show_reasoning: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """流式对话方法，支持实时输出推理过程和回答（异步版本）"""
        # 添加用户消息到历史
        self.conversation_history.append({"role": "user", "content": message})
        
        # 构造请求数据
        data = {
            "model_name": model_name,
            "messages": self.conversation_history,
            "show_reasoning": show_reasoning,
            "char_by_char": True  # 启用逐字输出模式
        }
        
        try:
            # 使用aiohttp进行异步请求
            async with ClientSession(timeout=ClientTimeout(total=60, connect=0.5)) as session:
                async with session.post(
                    f"{self.base_url}/conversation_stream",
                    json=data,
                    headers=self.headers
                ) as response:
                    response.raise_for_status()
                    
                    # 初始化变量
                    final_response = ""
                    
                    # 立即发送连接状态
                    yield {"status": "connected", "message": "已连接到服务器"}
                    
                    # 处理SSE流，优化为逐字符处理
                    async for line in response.content:
                        line = line.decode('utf-8')
                        
                        # 直接处理每一行数据，不使用缓冲区
                        if line.startswith('data: '):
                            data_str = line[6:]
                            
                            if data_str:
                                    try:
                                        chunk_data = json.loads(data_str)
                                        yield chunk_data
                                        
                                        # 保存最终响应用于历史记录
                                        if "response" in chunk_data and chunk_data["response"]:
                                            final_response = chunk_data["response"]
                                    except json.JSONDecodeError:
                                        yield {"error": "无法解析服务器响应"}
                            else:
                                buffer = ""
                    
                    # 将最终助手消息添加到历史记录
                    if final_response:
                        self.conversation_history.append({"role": "assistant", "content": final_response})
                        
                    # 发送完成状态
                    yield {"status": "completed"}
        except aiohttp.ClientResponseError as e:
            yield {"error": f"HTTP错误: {e.status} - {e.message}"}
        except aiohttp.ClientError as e:
            yield {"error": f"请求异常: {str(e)}"}
        except asyncio.TimeoutError:
            yield {"error": "连接超时，请检查服务器状态或网络连接"}
        except Exception as e:
            yield {"error": f"未知错误: {str(e)}"}

if __name__ == "__main__":
    client = MCPClient()
    
    # 先检查服务是否可用
    if not client._check_connection():
        print("错误: 无法连接到MCP服务，请确保服务已启动")
        exit(1)
    
    # 测试空模型名称
    print("测试空模型名称:")
    result = client.conversation("dsv3", "常见的十字花科植物有哪些？")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    
    # # 测试不存在的模型
    # print("\n测试不存在的模型:")
    # result = client.generate("nonexistent", "你好")
    # print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # # 测试正确的模型
    # print("\n测试正确的模型:")
    # models = client.list_models()
    # if "models" in models and models["models"]:
    #     model_name = models["models"][0]
    #     result = client.generate(model_name, "你好")
    #     print(json.dumps(result, indent=2, ensure_ascii=False))
