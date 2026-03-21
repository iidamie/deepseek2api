import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from utils.logger import logger
from auth import get_auth_headers
from deepseek import stop_deepseek_stream, delete_deepseek_session

router = APIRouter()


@router.post("/v1/chat/completions/stop")
async def stop_stream(request: Request):
    """停止 OpenAI 格式的流式响应"""
    try:
        req_data = await request.json()
        session_id = req_data.get("session_id")
        request_id = req_data.get("request_id")
        
        if not session_id or not request_id:
            raise HTTPException(status_code=400, detail="Missing session_id or request_id")
        
        token = getattr(request.state, "deepseek_token", "")
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")
        
        # 停止流式响应
        success = stop_deepseek_stream(token, session_id, request_id)
        
        if success:
            # 删除会话
            delete_deepseek_session(token, session_id)
            return JSONResponse(content={"status": "stopped"})
        else:
            raise HTTPException(status_code=500, detail="Failed to stop stream")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[stop_stream] 异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/messages/stop")
async def claude_stop_stream(request: Request):
    """停止 Claude 格式的流式响应"""
    try:
        req_data = await request.json()
        session_id = req_data.get("session_id")
        request_id = req_data.get("request_id")
        
        if not session_id or not request_id:
            raise HTTPException(status_code=400, detail="Missing session_id or request_id")
        
        token = getattr(request.state, "deepseek_token", "")
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")
        
        # 停止流式响应
        success = stop_deepseek_stream(token, session_id, request_id)
        
        if success:
            # 删除会话
            delete_deepseek_session(token, session_id)
            return JSONResponse(content={"type": "message_stop"})
        else:
            raise HTTPException(status_code=500, detail="Failed to stop stream")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[claude_stop_stream] 异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/messages/count_tokens")
async def claude_count_tokens(request: Request):
    """Claude token 计数接口"""
    try:
        req_data = await request.json()
        messages = req_data.get("messages", [])
        system_prompt = req_data.get("system", "")
        
        # 简单估算：每个字符约 0.25 token
        total_chars = len(system_prompt)
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        total_chars += len(item.get("text", ""))
            else:
                total_chars += len(content)
        
        estimated_tokens = int(total_chars * 0.25)
        
        return JSONResponse(content={"input_tokens": estimated_tokens})
        
    except Exception as e:
        logger.error(f"[claude_count_tokens] 异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))
