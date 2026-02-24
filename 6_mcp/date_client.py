import json
import mcp
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters
from openai import AsyncOpenAI

params = StdioServerParameters(command="uv", args=["run", "date_server.py"], env=None)


async def list_date_tools():
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return tools_result.tools


async def call_date_tool(tool_name: str, tool_args: dict):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)
            return result.content[0].text


def mcp_tool_to_openai_schema(tool) -> dict:
    """Convert an MCP tool definition to the OpenAI function-calling schema."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {**tool.inputSchema, "additionalProperties": False},
            "strict": True,
        },
    }


async def ask_with_date_tools(question: str) -> str:
    """Ask a question to GPT using the date MCP server tools via a native OpenAI call."""
    client = AsyncOpenAI()

    mcp_tools = await list_date_tools()
    openai_tools = [mcp_tool_to_openai_schema(t) for t in mcp_tools]

    messages = [{"role": "user", "content": question}]

    while True:
        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            tools=openai_tools,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            messages.append(choice.message)
            for tool_call in choice.message.tool_calls:
                tool_args = json.loads(tool_call.function.arguments)
                tool_result = await call_date_tool(tool_call.function.name, tool_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })
        else:
            return choice.message.content
