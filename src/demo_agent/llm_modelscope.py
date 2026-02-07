from __future__ import annotations
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def make_client():
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model_id = os.getenv("LLM_MODEL_ID")
    if not api_key or not base_url or not model_id:
        return None, None
    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, model_id

TOOLS = [
    {"type": "function", "function": {"name": "run_tests", "description": "Run unit tests", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "apply_patch", "description": "Write file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "network_install", "description": "Install package using network", "parameters": {"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]}}},
]

def chat_once(messages):
    client, model_id = make_client()
    if client is None:
        raise RuntimeError("LLM not configured")
    return client.chat.completions.create(
        model=model_id,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.2,
    )
