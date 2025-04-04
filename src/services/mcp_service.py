from typing import Dict, List, Any
import time
from ..models.base import BaseModel, VolcEngineModel

class MCPService:
    def __init__(self):
        self.models: Dict[str, BaseModel] = {}
        self.request_stats = {
            'total_requests': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0
        }
        
    def init_models(self, config: Dict[str, Any]):
        """初始化所有配置中的模型"""
        for model_type, model_config in config.items():
            if model_type in ['openai', 'anthropic']:
                model = BaseModel(model_config)
                self.register_model(model_type, model)
            elif model_type in ['dsr1', 'dsv3']:
                model = VolcEngineModel(model_config)
                self.register_model(model_type, model)

    def register_model(self, name: str, model: BaseModel):
        self.models[name] = model

    async def generate(self, model_name: str, prompt: str) -> str:
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
        
        start_time = time.time()
        result = await self.models[model_name].generate(prompt)
        elapsed = time.time() - start_time
        
        self._update_stats(elapsed)
        print(f"[PERF] generate request took {elapsed:.3f} seconds")
        return result

    async def generate_all(self, prompt: str) -> Dict[str, str]:
        start_time = time.time()
        results = {}
        for name, model in self.models.items():
            results[name] = await model.generate(prompt)
        
        elapsed = time.time() - start_time
        self._update_stats(elapsed)
        print(f"[PERF] generate_all request took {elapsed:.3f} seconds")
        return results

    async def conversation(self, model_name: str, messages: List[Dict[str, str]], show_reasoning: bool = False) -> Dict[str, Any]:
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
            
        start_time = time.time()
        
        # 直接将show_reasoning参数传递给模型的conversation方法
        # 所有模型的conversation方法都应该支持show_reasoning参数
        result = await self.models[model_name].conversation(messages, show_reasoning)
        
        # 处理返回结果
        if isinstance(result, dict):
            # 如果返回的是字典，直接使用
            response = result
        else:
            # 如果返回的是字符串，封装为字典
            response = {"response": result}
            
        elapsed = time.time() - start_time
        
        self._update_stats(elapsed)
        print(f"[PERF] conversation request took {elapsed:.3f} seconds")
        return response
        
    async def conversation_stream(self, model_name: str, messages: List[Dict[str, str]], show_reasoning: bool = False, char_by_char: bool = True):
        """流式对话方法，支持实时输出推理过程"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
            
        start_time = time.time()
        
        # 添加系统消息，要求模型展示推理过程
        system_message = {"role": "system", "content": "请先进行思考，分析问题并给出推理过程，然后再给出最终答案。格式为：\n\n思考：[你的分析和推理过程]\n\n回答：[你的最终答案]"}
        
        # 处理消息列表
        dict_messages = []
        for msg in messages:
            if hasattr(msg, "model_dump"):
                dict_messages.append(msg.model_dump())
            elif hasattr(msg, "dict"):
                dict_messages.append(msg.dict())
            else:
                dict_messages.append(msg)
        
        # 检查是否已有系统消息
        has_system = any(msg.get("role", "") == "system" for msg in dict_messages if isinstance(msg, dict))
        
        # 构建新的消息列表
        if has_system:
            new_messages = []
            for msg in dict_messages:
                if isinstance(msg, dict) and msg.get("role", "") == "system":
                    msg["content"] = system_message["content"]
                new_messages.append(msg)
        else:
            new_messages = [system_message] + dict_messages
        
        # 使用流式输出
        try:
            # 初始化变量
            full_response = ""
            reasoning = ""
            answer = ""
            
            # 使用状态机模式处理流式输出
            state = {
                "phase": "init",  # 初始状态
                "reasoning": "",
                "response": "",
                "last_yield_time": time.time(),
                "yield_interval": 0.0  # 已移除输出频率限制，但还需要进一步优化
            }
            
            # 调用模型的流式API
            async for chunk in self.models[model_name].conversation_stream(new_messages):
                if not chunk:
                    continue
                    
                full_response += chunk
                now = time.time()
                
                # 状态机处理逻辑
                if state["phase"] == "init":
                    # 检测是否进入推理阶段
                    if "思考：" in full_response:
                        state["phase"] = "reasoning"
                        reasoning_text = full_response.split("思考：", 1)[1]
                        state["reasoning"] = reasoning_text
                        if show_reasoning:
                            # 移除时间间隔检查，立即输出每个字符
                            yield {"reasoning": reasoning_text, "response": ""}
                            state["last_yield_time"] = now
                
                elif state["phase"] == "reasoning":
                    # 检测是否进入回答阶段
                    if "回答：" in full_response:
                        state["phase"] = "response"
                        parts = full_response.split("回答：", 1)
                        reasoning_part = parts[0].split("思考：", 1)[1] if "思考：" in parts[0] else ""
                        response_text = parts[1]
                        
                        state["reasoning"] = reasoning_part
                        state["response"] = response_text
                        
                        yield {"reasoning": reasoning_part if show_reasoning else "", "response": response_text}
                        state["last_yield_time"] = now
                    else:
                        # 仍在推理阶段，更新推理内容
                        new_reasoning = full_response.split("思考：", 1)[1]
                        if new_reasoning != state["reasoning"] and show_reasoning:
                            state["reasoning"] = new_reasoning
                            # 移除时间间隔检查，立即输出每个字符
                            yield {"reasoning": new_reasoning, "response": ""}
                            state["last_yield_time"] = now
                
                elif state["phase"] == "response":
                    # 已进入回答阶段，持续更新回答内容
                    if "回答：" in full_response:
                        new_response = full_response.split("回答：", 1)[1]
                        if new_response != state["response"]:
                            state["response"] = new_response
                            # 移除时间间隔检查，立即输出每个字符
                            yield {"reasoning": state["reasoning"] if show_reasoning else "", "response": new_response}
                            state["last_yield_time"] = now
            
            # 最终处理，确保完整输出
            if state["phase"] == "init":
                # 如果没有检测到标记，将全部内容作为回答
                yield {"reasoning": "", "response": full_response}
            elif state["phase"] == "reasoning":
                # 如果只有推理没有回答，将推理内容也作为回答
                yield {"reasoning": state["reasoning"] if show_reasoning else "", "response": state["reasoning"]}
            else:
                # 确保最终结果完整输出
                if "回答：" in full_response:
                    final_response = full_response.split("回答：", 1)[1]
                    final_reasoning = full_response.split("思考：", 1)[1].split("回答：", 1)[0] if "思考：" in full_response else ""
                    yield {"reasoning": final_reasoning if show_reasoning else "", "response": final_response}
                
        except Exception as e:
            yield {"error": str(e)}
            
        elapsed = time.time() - start_time
        self._update_stats(elapsed)
        print(f"[PERF] conversation_stream request took {elapsed:.3f} seconds")
        
    def _update_stats(self, elapsed: float):
        """更新请求统计信息"""
        self.request_stats['total_requests'] += 1
        self.request_stats['total_time'] += elapsed
        self.request_stats['min_time'] = min(self.request_stats['min_time'], elapsed)
        self.request_stats['max_time'] = max(self.request_stats['max_time'], elapsed)