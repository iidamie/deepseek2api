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
        
        # 认证
        mode, token = determine_mode_and_token(request)
        if not token:
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # 准备消息
        messages = messages_prepare(messages)
        
        # 创建会话
        session_id = create_session(request)
        if not session_id:
            raise HTTPException(status_code=500, detail="Failed to create session")
        
        # 获取 PoW 响应
        pow_answer = get_pow_response(request)
        if not pow_answer:
            raise HTTPException(status_code=401, detail="Failed to get PoW response")
        
        # 调用 DeepSeek API
        try:
            resp = call_deepseek_completion(
                token=token,
                session_id=session_id,
                messages=messages,
                model=model,
                temperature=temperature,
                stream=stream,
                pow_answer=pow_answer,
            )
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
