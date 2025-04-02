from mcp_client import MCPClient  # 修改为直接导入

client = MCPClient()

# 第一轮对话
response1 = client.conversation("dsr1", "你好")
print(response1)

# 第二轮对话(会记住上下文)
response2 = client.conversation("dsr1", "我刚才问了什么？")
print(response2)