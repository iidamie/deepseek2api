from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from utils.logger import logger
from routes import models_router, openai_router, claude_router, utils_router

# 创建 FastAPI 应用
app = FastAPI(title="DeepSeek2API", version="1.0.0")

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(models_router)
app.include_router(openai_router)
app.include_router(claude_router)
app.include_router(utils_router)


@app.get("/")
async def index():
    """首页"""
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DeepSeek2API</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                }
                h1 { color: #333; }
                .endpoint {
                    background: #f5f5f5;
                    padding: 10px;
                    margin: 10px 0;
                    border-radius: 5px;
                }
                code {
                    background: #e0e0e0;
                    padding: 2px 5px;
                    border-radius: 3px;
                }
            </style>
        </head>
        <body>
            <h1>DeepSeek2API</h1>
            <p>将 DeepSeek 官网接口转换为 OpenAI 和 Claude 兼容格式</p>
            
            <h2>可用接口</h2>
            
            <div class="endpoint">
                <strong>GET /v1/models</strong><br>
                获取 OpenAI 格式的模型列表
            </div>
            
            <div class="endpoint">
                <strong>POST /v1/chat/completions</strong><br>
                OpenAI 兼容的对话补全接口
            </div>
            
            <div class="endpoint">
                <strong>POST /v1/messages</strong><br>
                Claude 兼容的消息接口
            </div>
            
            <div class="endpoint">
                <strong>GET /v1/models/claude</strong><br>
                获取 Claude 格式的模型列表
            </div>
            
            <h2>使用方法</h2>
            <p>在请求头中添加 <code>Authorization: Bearer YOUR_TOKEN</code></p>
            <p>详细文档请参考 <a href="https://github.com/iidamie/deepseek2api">GitHub</a></p>
        </body>
        </html>
        """
    )


if __name__ == "__main__":
    import uvicorn
    logger.info("DeepSeek2API 启动中...")
    uvicorn.run(app, host="0.0.0.0", port=5001)
