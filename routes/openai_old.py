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
        # 非流式响应实际上也是 SSE 格式，需要逐行解析
        logger.info(f"[handle_non_stream_response] 开始处理非流式响应")
        
        think_list = []
        text_list = []
        ptype = "text"
        
        for raw_line in resp.iter_lines():
            try:
                line = raw_line.decode("utf-8")
            except Exception as e:
                logger.warning(f"[handle_non_stream_response] 解码失败: {e}")
                continue
            
            if not line:
                continue
            
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                
                try:
                    chunk = json.loads(data_str)
                    
                    # 提取 v 字段
                    if "v" in chunk:
                        v_value = chunk["v"]
                        
                        if "p" in chunk and chunk.get("p") == "response/status":
                            if v_value == 'FINISHED':
                                break
                            continue
                        
                        if "p" in chunk and chunk.get("p") == "response/search_status":
                            continue
                        
                        if "p" in chunk and chunk.get("p") == "response/thinking_content":
                            ptype = "thinking"
                        elif "p" in chunk and chunk.get("p") == "response/content":
                            ptype = "text"
                        
                        # 处理字符串形式的 v 值（即文本内容）
                        if isinstance(v_value, str):
                            if ptype == "thinking":
                                think_list.append(v_value)
                            else:
                                text_list.append(v_value)
                        
                        # 处理数组更新如状态变更
                        elif isinstance(v_value, list):
                            for item in v_value:
                                if item.get("p") == "status" and item.get("v") == "FINISHED":
                                    break
                
                except Exception as e:
                    logger.warning(f"[handle_non_stream_response] 无法解析: {data_str}, 错误: {e}")
                    continue
        
        # 构建最终内容
        final_reasoning = "".join(think_list)
        final_content = "".join(text_list)
        
        logger.info(f"[handle_non_stream_response] 收集完成: reasoning={len(final_reasoning)} chars, content={len(final_content)} chars")
        
        # 解析工具调用
        tool_calls_detected = None
        if tools:
            tool_calls_detected, final_content = parse_tool_calls_from_text(final_content)
        
        # 估算 token 数
        prompt_tokens = 0  # 简单估算
        reasoning_tokens = len(final_reasoning) // 4
        completion_tokens = len(final_content) // 4
        
        # 构建 message 对象
        message_obj = {
            "role": "assistant",
            "content": final_content,
        }
        
        # 添加 reasoning_content（如果有）
        if final_reasoning:
            message_obj["reasoning_content"] = final_reasoning
        
        # 如果检测到 tool_calls，添加到 message
        finish_reason = "stop"
        if tool_calls_detected:
            message_obj["tool_calls"] = tool_calls_detected
            finish_reason = "tool_calls"
        
        # 构造 OpenAI 格式响应
        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": message_obj,
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": reasoning_tokens + completion_tokens,
                "total_tokens": prompt_tokens + reasoning_tokens + completion_tokens,
                "completion_tokens_details": {
                    "reasoning_tokens": reasoning_tokens
                },
            },
        }
        
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
    stream_completed = False
    accumulated_content = ""
    accumulated_thinking = ""
    ptype = "text"
    
    try:
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            
            try:
                line = raw_line.decode("utf-8")
            except Exception as e:
                logger.warning(f"[stream_generator] 解码失败: {e}")
                continue
            
            if not line.startswith("data:"):
                continue
            
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                stream_completed = True
                break
            
            try:
                chunk = json.loads(data_str)
                
                # 检查是否有 v 字段（DeepSeek SSE 格式）
                if "v" not in chunk:
                    continue
                
                v_value = chunk["v"]
                
                # 检查状态
                if "p" in chunk and chunk.get("p") == "response/status":
                    if v_value == 'FINISHED':
                        stream_completed = True
                        break
                    continue
                
                # 跳过搜索状态
                if "p" in chunk and chunk.get("p") == "response/search_status":
                    continue
                
                # 确定内容类型
                if "p" in chunk and chunk.get("p") == "response/thinking_content":
                    ptype = "thinking"
                elif "p" in chunk and chunk.get("p") == "response/content":
                    ptype = "text"
                
                # 提取内容
                content = ""
                if isinstance(v_value, str):
                    content = v_value
                elif isinstance(v_value, list):
                    # 处理数组更新
                    for item in v_value:
                        if item.get("p") == "status" and item.get("v") == "FINISHED":
                            stream_completed = True
                            break
                    continue
                
                if not content:
                    continue
                
                # 累积内容
                if ptype == "thinking":
                    accumulated_thinking += content
                    # 发送 thinking 内容（如果需要）
                    chunk_data = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"reasoning_content": content},
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
