import json
import time
import uuid
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from utils.logger import logger
from auth import determine_mode_and_token, get_auth_headers, release_account
from deepseek import get_pow_response, create_session, call_deepseek_completion, delete_deepseek_session, stop_deepseek_stream
from converters import messages_prepare, parse_tool_calls_from_text

router = APIRouter()


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI 兼容的对话补全接口"""
    try:
        req_data = await request.json()
        messages = req_data.get("messages", [])
        model = req_data.get("model", "deepseek-chat")
        stream = req_data.get("stream", False)
        temperature = req_data.get("temperature", 1.0)
        max_tokens = req_data.get("max_tokens", 4096)
        tools = req_data.get("tools", [])
        
        # 判断是否启用思考模式
        thinking_enabled = "reasoner" in model.lower() or "r1" in model.lower()
        search_enabled = False
        
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
            
            # 将工具提示插入到 messages 的开头（如果没有 system 消息）
            system_found = any(msg.get("role") == "system" for msg in messages)
            if not system_found:
                messages.insert(0, {"role": "system", "content": tool_system_prompt})
        
        # 判断模式并获取 token
        determine_mode_and_token(request)
        
        # 使用 messages_prepare 函数构造最终 prompt
        final_prompt = messages_prepare(messages)
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
            "thinking_enabled": thinking_enabled,
            "search_enabled": search_enabled,
        }
        
        # 调用 DeepSeek API
        resp = call_deepseek_completion(headers, payload, stream=stream)
        
        if not stream:
            # 非流式响应
            return await handle_non_stream_response(request, resp, session_id, model, tools)
        else:
            # 流式响应
            return StreamingResponse(
                stream_generator(request, resp, session_id, model, tools),
                media_type="text/event-stream"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[chat_completions] 异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_non_stream_response(request: Request, resp, session_id: str, model: str, tools: list):
    """处理非流式响应"""
    try:
        data = resp.json()
        
        if data.get("code") != 0:
            error_msg = data.get("msg", "Unknown error")
            logger.error(f"[handle_non_stream_response] DeepSeek API 错误: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        content = data["data"]["biz_data"]["choices"][0]["message"]["content"]
        
        # 解析工具调用
        clean_content, tool_calls = parse_tool_calls_from_text(content) if tools else (content, [])
        
        # 构造 OpenAI 格式响应
        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": clean_content,
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
        
        if tool_calls:
            response["choices"][0]["message"]["tool_calls"] = tool_calls
        
        # 删除会话
        mode = "config" if hasattr(request.state, "use_config_token") and request.state.use_config_token else "user"
        account = getattr(request.state, "account", None)
        token = getattr(request.state, "deepseek_token", "")
        
        delete_deepseek_session(token, session_id)
        
        if mode == "config" and account:
            release_account(account)
        
        return JSONResponse(content=response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[handle_non_stream_response] 异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def stream_generator(request: Request, resp, session_id: str, model: str, tools: list):
    """流式响应生成器"""
    request_id = None
    stream_completed = False
    accumulated_content = ""
    
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
                
                if content:
                    accumulated_content += content
                    
                    chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": content},
                                "finish_reason": None,
                            }
                        ],
                    }
                    
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                finish_reason = choices[0].get("finish_reason")
                if finish_reason:
                    stream_completed = True
                    
                    # 解析工具调用
                    if tools:
                        clean_content, tool_calls = parse_tool_calls_from_text(accumulated_content)
                        if tool_calls:
                            for tool_call in tool_calls:
                                chunk = {
                                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": model,
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {"tool_calls": [tool_call]},
                                            "finish_reason": None,
                                        }
                                    ],
                                }
                                yield f"data: {json.dumps(chunk)}\n\n"
                    
                    # 发送结束 chunk
                    chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop",
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    break
                    
            except json.JSONDecodeError:
                continue
    
    except GeneratorExit:
        logger.info(f"[stream_generator] 客户端断开连接")
        stream_completed = False
    except Exception as e:
        logger.error(f"[stream_generator] 流式处理异常: {e}")
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
