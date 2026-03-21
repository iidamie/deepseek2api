import json
import time
import uuid
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from utils.logger import logger
from auth import determine_claude_mode_and_token, get_auth_headers, release_account
from deepseek import get_pow_response, create_session, call_deepseek_completion, delete_deepseek_session, stop_deepseek_stream
from converters import claude_to_openai_messages, openai_to_claude_response, openai_stream_to_claude_stream, messages_prepare

router = APIRouter()

CLAUDE_DEFAULT_MODEL = "claude-3-5-sonnet-20241022"


@router.post("/v1/messages")
async def claude_messages(request: Request):
    """Claude 兼容的消息接口"""
    try:
        req_data = await request.json()
        claude_messages = req_data.get("messages", [])
        model = req_data.get("model", CLAUDE_DEFAULT_MODEL)
        system_prompt = req_data.get("system", "")
        stream = req_data.get("stream", False)
        max_tokens = req_data.get("max_tokens", 4096)
        temperature = req_data.get("temperature", 1.0)
        
        # 转换为 OpenAI 格式
        openai_messages = claude_to_openai_messages(claude_messages, system_prompt)
        
        # 判断模式并获取 token
        determine_claude_mode_and_token(request)
        
        # 使用 messages_prepare 函数构造最终 prompt
        final_prompt = messages_prepare(openai_messages)
        
        session_id = create_session(request)
        if not session_id:
            raise HTTPException(status_code=401, detail="invalid token.")
        
        pow_resp = get_pow_response(request)
        if not pow_resp:
            raise HTTPException(
                status_code=401,
                detail="Failed to get PoW (invalid token or unknown error).",
            )
        
        headers = {**get_auth_headers(request), "x-ds-pow-response": pow_resp}
        payload = {
            "chat_session_id": session_id,
            "parent_message_id": None,
            "prompt": final_prompt,
            "ref_file_ids": [],
            "thinking_enabled": False,
            "search_enabled": False,
        }
        
        # 调用 DeepSeek API
        resp = call_deepseek_completion(headers, payload, stream=stream)
        
        if not stream:
            # 非流式响应
            return await handle_claude_non_stream_response(request, resp, session_id, model)
        else:
            # 流式响应
            return StreamingResponse(
                claude_stream_generator(request, resp, session_id, model),
                media_type="text/event-stream"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[claude_messages] 异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_claude_non_stream_response(request: Request, resp, session_id: str, model: str):
    """处理 Claude 非流式响应"""
    try:
        data = resp.json()
        
        if data.get("code") != 0:
            error_msg = data.get("msg", "Unknown error")
            logger.error(f"[handle_claude_non_stream_response] DeepSeek API 错误: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        content = data["data"]["biz_data"]["choices"][0]["message"]["content"]
        
        # 构造 OpenAI 格式响应
        openai_response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "deepseek-chat",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }
        
        # 转换为 Claude 格式
        claude_response = openai_to_claude_response(openai_response, model)
        
        # 删除会话
        mode = "config" if hasattr(request.state, "use_config_token") and request.state.use_config_token else "user"
        account = getattr(request.state, "account", None)
        token = getattr(request.state, "deepseek_token", "")
        
        delete_deepseek_session(token, session_id)
        
        if mode == "config" and account:
            release_account(account)
        
        return JSONResponse(content=claude_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[handle_claude_non_stream_response] 异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def claude_stream_generator(request: Request, resp, session_id: str, model: str):
    """Claude 流式响应生成器"""
    request_id = None
    stream_completed = False
    first_chunk = True
    
    try:
        for line in resp.iter_lines():
            if not line:
                continue
            
            line = line.decode("utf-8")
            if not line.startswith("data: "):
                continue
            
            data_str = line[6:]
            if data_str == "[DONE]":
                stream_completed = True
                break
            
            try:
                data = json.loads(data_str)
                
                # 提取 request_id
                if not request_id and "request_id" in data.get("data", {}).get("biz_data", {}):
                    request_id = data["data"]["biz_data"]["request_id"]
                
                choices = data.get("data", {}).get("biz_data", {}).get("choices", [])
                if not choices:
                    continue
                
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                role = delta.get("role")
                
                # 构造 OpenAI 格式 chunk
                openai_chunk = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "deepseek-chat",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": None,
                        }
                    ],
                }
                
                if role:
                    openai_chunk["choices"][0]["delta"]["role"] = role
                if content:
                    openai_chunk["choices"][0]["delta"]["content"] = content
                
                finish_reason = choices[0].get("finish_reason")
                if finish_reason:
                    stream_completed = True
                    openai_chunk["choices"][0]["finish_reason"] = "stop"
                
                # 转换为 Claude 流式格式
                claude_events = openai_stream_to_claude_stream(openai_chunk, model)
                
                for event in claude_events:
                    yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
                
                if finish_reason:
                    break
                    
            except json.JSONDecodeError:
                continue
    
    except GeneratorExit:
        logger.info(f"[claude_stream_generator] 客户端断开连接")
        stream_completed = False
    except Exception as e:
        logger.error(f"[claude_stream_generator] 流式处理异常: {e}")
    finally:
        # 清理资源
        mode = "config" if hasattr(request.state, "use_config_token") and request.state.use_config_token else "user"
        account = getattr(request.state, "account", None)
        token = getattr(request.state, "deepseek_token", "")
        
        if not stream_completed and request_id:
            stop_deepseek_stream(token, session_id, request_id)
        
        delete_deepseek_session(token, session_id)
        
        if mode == "config" and account:
            release_account(account)
