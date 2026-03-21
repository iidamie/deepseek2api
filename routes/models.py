from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

# Claude 模型列表
CLAUDE_MODELS = [
    {
        "id": "claude-3-5-sonnet-20241022",
        "object": "model",
        "created": 1729641600,
        "owned_by": "anthropic",
    },
    {
        "id": "claude-3-5-sonnet-20240620",
        "object": "model",
        "created": 1718841600,
        "owned_by": "anthropic",
    },
    {
        "id": "claude-3-opus-20240229",
        "object": "model",
        "created": 1709251200,
        "owned_by": "anthropic",
    },
    {
        "id": "claude-3-sonnet-20240229",
        "object": "model",
        "created": 1709251200,
        "owned_by": "anthropic",
    },
    {
        "id": "claude-3-haiku-20240307",
        "object": "model",
        "created": 1709769600,
        "owned_by": "anthropic",
    },
]

# OpenAI 模型列表
OPENAI_MODELS = [
    {
        "id": "deepseek-chat",
        "object": "model",
        "created": 1677649963,
        "owned_by": "deepseek",
    },
    {
        "id": "deepseek-reasoner",
        "object": "model",
        "created": 1677649963,
        "owned_by": "deepseek",
    },
]


@router.get("/v1/models")
async def list_models():
    """OpenAI 兼容的模型列表接口"""
    return JSONResponse(content={"object": "list", "data": OPENAI_MODELS})


@router.get("/v1/models/claude")
async def list_claude_models():
    """Claude 模型列表接口"""
    return JSONResponse(content={"object": "list", "data": CLAUDE_MODELS})
