"""
OpenAI 兼容接口路由
"""
import json
import time
import uuid
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from utils.logger import logger
from auth.token import determine_mode_and_token
from deepseek.session import create_session, delete_deepseek_session
from deepseek.pow import get_pow_response
from deepseek.api import call_deepseek_completion
from converters.messages import messages_prepare, parse_tool_calls_from_text

router = APIRouter()


@router.get("/v1/models")
async def list_models():
    """列出可用模型"""
    models = [
        {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},
        {"id": "deepseek-reasoner", "object": "model", "owned_by": "deepseek"},
    ]
    return {"object": "list", "data": models}


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI 兼容的聊天补全接口"""
    try:
        body = await request.json()
        
        # 提取参数
        messages = body.get("messages", [])
        model = body.get("model", "deepseek-chat")
        temperature = body.get("temperature", 1.0)
        stream = body.get("stream", False)
        tools = body.get("tools", [])
        
        # 判断是否启用思考模式
        thinking_enabled = "reasoner" in model.lower() or "r1" in model.lower()
        search_enabled = False
        
        # 认证
        determine_mode_and_token(request)
        token = request.state.deepseek_token
        if not token:
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # 处理工具调用
        if tools:
            # 构造工具系统提示
            tool_descriptions = []
            for tool in tools:
                func = tool.get("function", {})
                tool_descriptions.append(
                    f"- {func.get('name')}: {func.get('description', '')}"
                )
            
            tool_system_prompt = (
                "You have access to the following tools:\n"
                + "\n".join(tool_descriptions)
                + "\n\nTo use a tool, respond with: <tool_call>{\"name\": \"tool_name\", \"arguments\": {...}}</tool_call>"
            )
            
            # 将工具提示插入到消息开头
            if messages and messages[0].get("role") == "system":
                messages[0]["content"] = tool_system_prompt + "\n\n" + messages[0]["content"]
            else:
                messages.insert(0, {"role": "system", "content": tool_system_prompt})
        
        # 准备消息
        final_prompt = messages_prepare(messages)
        
        # 创建会话
        session_id = create_session(request)
        if not session_id:
            raise HTTPException(status_code=500, detail="Failed to create session")
        
        # 获取 PoW 响应
        pow_answer = get_pow_response(request)
        if not pow_answer:
            raise HTTPException(status_code=401, detail="Failed to get PoW response")
        
        # 构建请求头和负载
        from auth.token import get_auth_headers
        headers = get_auth_headers(request)
        
        payload = {
            "chat_session_id": session_id,
            "parent_message_id": None,
            "prompt": final_prompt,
            "ref_file_ids": [],
            "thinking_enabled": thinking_enabled,
            "search_enabled": search_enabled,
        }
        
        # 调用 DeepSeek API
        try:
            resp = call_deepseek_completion(headers, payload, stream=stream)
        except Exception as e:
            logger.error(f"[chat_completions] 调用 DeepSeek API 失败: {e}")
            delete_deepseek_session(request, session_id)
            raise HTTPException(status_code=500, detail=str(e))
        
        # 返回响应
        if stream:
            return StreamingResponse(
                stream_generator(request, resp, session_id, model, tools),
                media_type="text/event-stream",
            )
        else:
            return await handle_non_stream_response(request, resp, session_id, model, tools)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[chat_completions] 未知错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
