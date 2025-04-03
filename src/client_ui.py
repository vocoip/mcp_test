
import argparse
import json
import time
import sys
import os
import asyncio
import platform
from typing import Optional, Dict, Any
import colorama
from colorama import Fore, Style

# 添加当前目录到系统路径，以便能够导入同级模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.mcp_client import MCPClient

def display_models(models):
    """显示可用模型列表"""
    if not models:
        print("当前没有可用的模型")
        return
    
    print("\n可用的模型列表:")
    for i, model in enumerate(models, 1):
        # 添加模型类型标识
        if model.startswith("ep-") or model.startswith("vds"):
            print(f"{i}. {model} (VolcEngine)")
        elif model.startswith("deepseek") or model.startswith("ds"):
            print(f"{i}. {model} (DeepSeek)")
        else:
            print(f"{i}. {model}")
    print()

def main():
    parser = argparse.ArgumentParser(description='MCP客户端交互界面')
    parser.add_argument('--url', default='http://127.0.0.1:8088', help='MCP服务地址')
    parser.add_argument('--show-reasoning', action='store_true', help='显示模型推理过程')
    args = parser.parse_args()
    
    client = MCPClient(args.url)
    
    # 检查服务连接
    if not client._check_connection():
        print("错误: 无法连接到MCP服务，请确保服务已启动")
        return
    
    print("欢迎使用MCP客户端交互界面")
    print("输入'exit'退出对话，输入'switch'切换模型，输入'reasoning'切换推理过程显示")
    print("当前支持模型类型: VolcEngine, DeepSeek")
    
    # 显示是否启用推理过程
    show_reasoning = args.show_reasoning
    if show_reasoning:
        print("已启用推理过程显示模式")
    else:
        print("提示: 使用 --show-reasoning 参数或输入'reasoning'命令可以显示模型的推理过程")
    
    # 获取可用模型列表
    models_response = client.list_models()
    models = models_response.get("models", [])
    
    if not models:
        print("警告: 没有找到可用的模型")
        model_name = input("请手动输入要使用的模型名称: ")
    else:
        display_models(models)
        while True:
            try:
                choice = input("请选择模型编号或直接输入模型名称: ")
                if choice.isdigit() and 1 <= int(choice) <= len(models):
                    model_name = models[int(choice) - 1]
                    break
                elif choice in models:
                    model_name = choice
                    break
                else:
                    print("无效的选择，请重新输入")
            except (ValueError, IndexError):
                print("无效的输入，请重新选择")
    
    print(f"\n已选择模型: {model_name}\n")
    
    # 交互循环
    while True:
        message = input("你: ")
        if message.lower() == 'exit':
            break
        elif message.lower() == 'reasoning':
            # 切换推理过程显示状态
            show_reasoning = not show_reasoning
            if show_reasoning:
                print("已启用推理过程显示模式")
            else:
                print("已关闭推理过程显示模式")
            continue
        elif message.lower() == 'switch':
            # 重新选择模型
            if models:
                display_models(models)
                while True:
                    try:
                        choice = input("请选择模型编号或直接输入模型名称: ")
                        if choice.isdigit() and 1 <= int(choice) <= len(models):
                            model_name = models[int(choice) - 1]
                            break
                        elif choice in models:
                            model_name = choice
                            break
                        else:
                            print("无效的选择，请重新输入")
                    except (ValueError, IndexError):
                        print("无效的输入，请重新选择")
            else:
                model_name = input("请手动输入要使用的模型名称: ")
            print(f"\n已切换到模型: {model_name}\n")
            # 清空对话历史
            client.conversation_history = []
            continue
            
        # 发送请求并显示响应
        start_time = time.time()
        # 简化请求状态显示
        print("\r请求中...", end="", flush=True)
            
        # 使用流式对话功能
        try:
            current_reasoning = ""
            current_response = ""
            reasoning_started = False
            response_started = False
            waiting_message_shown = False
            data_received = False
            last_flush_time = time.time()
            flush_interval = 0.0005  # 进一步减少刷新间隔到0.5ms，提高输出流畅度
            
            # 清除请求状态提示
            print("\r请求中...", end="", flush=True)
            
            # 使用生成器表达式直接迭代流式响应，添加更快的初始响应
            for chunk in client.conversation_stream(model_name, message, show_reasoning):
                # 处理连接状态消息
                if "status" in chunk:
                    # 极简化连接状态显示，只在必要时显示
                    if chunk["status"] == "connected":
                        # 连接成功后立即清除请求状态，不等待数据接收
                        print("\r" + " " * 20 + "\r", end="", flush=True)
                    elif chunk["status"] == "waiting" and "message" in chunk and not waiting_message_shown:
                        # 只在等待时间较长时显示一次等待消息
                        print("\r正在等待模型响应...", end="", flush=True)
                        waiting_message_shown = True
                    continue
                
                # 标记已收到数据，立即清除请求状态
                if not data_received and ("reasoning" in chunk or "response" in chunk):
                    print("\r" + " " * 20 + "\r", end="", flush=True)  # 清除整行的请求状态
                    data_received = True
                    # 立即刷新输出缓冲区
                    print("", end="", flush=True)
                
                # 处理错误消息
                if "error" in chunk:
                    # 添加换行确保错误消息显示在新行
                    if response_started or reasoning_started:
                        print("\n")
                    print(f"错误: {chunk['error']}")
                    break
                    
                # 处理推理过程的实时输出
                if show_reasoning and "reasoning" in chunk and chunk["reasoning"]:
                    new_reasoning = chunk["reasoning"]
                    if not reasoning_started:
                        print("思考过程:")
                        reasoning_started = True
                    
                    # 只打印新增的部分，并立即刷新
                    if len(new_reasoning) > len(current_reasoning):
                        new_content = new_reasoning[len(current_reasoning):]
                        # 逐字符输出以提高流畅度
                        for char in new_content:
                            print(char, end="", flush=True)
                            # 极小延迟，几乎不可察觉但能提高流畅度
                            time.sleep(0.0001)
                        current_reasoning = new_reasoning
                        last_flush_time = time.time()
                
                # 处理回答的实时输出
                if "response" in chunk and chunk["response"]:
                    new_response = chunk["response"]
                    if not response_started:
                        if reasoning_started:
                            print("\n\n-----------------\n")
                        print("AI: ", end="", flush=True)
                        response_started = True
                    
                    # 只打印新增的部分，并立即刷新
                    if len(new_response) > len(current_response):
                        new_content = new_response[len(current_response):]
                        # 逐字符输出以提高流畅度
                        for char in new_content:
                            print(char, end="", flush=True)
                            # 极小延迟，几乎不可察觉但能提高流畅度
                            time.sleep(0.0001)
                        current_response = new_response
                        last_flush_time = time.time()
                
                # 强制定期刷新输出缓冲区，确保流畅显示
                current_time = time.time()
                if current_time - last_flush_time > flush_interval:
                    # 使用空字符串刷新，减少视觉干扰
                    print("", end="", flush=True)
                    last_flush_time = current_time
                    
                # 动态调整延迟，在有数据时减少延迟，提高响应性
                if data_received:
                    time.sleep(0.0002)  # 数据流动时使用更小的延迟
                else:
                    time.sleep(0.0005)  # 等待数据时使用稍大的延迟
            
            # 完成后打印换行和耗时
            elapsed_time = time.time() - start_time
            print(f"\n\n(响应耗时: {elapsed_time:.2f}秒)")
            
        except Exception as e:
            print(f"错误: {str(e)}")
            # 如果流式输出失败，回退到普通对话方法
            print("流式输出失败，使用普通对话方法...")
            response = client.conversation(model_name, message, show_reasoning)
            elapsed_time = time.time() - start_time
            
            if "error" in response:
                print(f"错误: {response['error']}")
            else:
                # 如果有推理过程且启用了显示推理过程，先显示推理过程
                if show_reasoning and "reasoning" in response and response["reasoning"]:
                    print(f"\n思考过程:\n{response['reasoning']}")
                    print("\n-----------------\n")
                
                print(f"AI: {response['response']}")
                print(f"\n(响应耗时: {elapsed_time:.2f}秒)")

if __name__ == "__main__":
    main()