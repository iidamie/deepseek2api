# 项目结构说明

本项目已重构为模块化结构，便于维护和扩展。

## 目录结构

```
deepseek2api/
├── app.py                    # 主入口，FastAPI 应用和路由注册
├── config.py                 # 配置加载和管理
├── auth/                     # 认证模块
│   ├── __init__.py
│   ├── account.py           # 账号管理（登录、选择、释放）
│   └── token.py             # Token 处理和认证
├── deepseek/                 # DeepSeek API 模块
│   ├── __init__.py
│   ├── session.py           # 会话管理（创建、删除）
│   ├── pow.py               # PoW 计算
│   └── api.py               # DeepSeek API 调用
├── converters/               # 格式转换模块
│   ├── __init__.py
│   ├── claude.py            # Claude 格式转换
│   └── messages.py          # 消息预处理和工具调用解析
├── routes/                   # 路由模块
│   ├── __init__.py
│   ├── openai.py            # OpenAI 兼容接口
│   ├── claude.py            # Claude 兼容接口
│   └── models.py            # 模型列表接口
└── utils/                    # 工具模块
    ├── __init__.py
    └── logger.py            # 日志配置
```

## 模块说明

### auth/ - 认证模块
- `account.py`: 账号池管理，包括登录、选择、释放账号
- `token.py`: Token 认证，判断配置模式或用户自带 token 模式

### deepseek/ - DeepSeek API 模块
- `pow.py`: PoW 挑战计算
- `session.py`: 会话创建和删除
- `api.py`: DeepSeek API 调用封装

### converters/ - 格式转换模块
- `messages.py`: OpenAI 消息格式预处理，工具调用解析
- `claude.py`: Claude 和 OpenAI 格式互转

### routes/ - 路由模块
- `openai.py`: `/v1/chat/completions` 接口实现
- `claude.py`: `/v1/messages` 接口实现
- `models.py`: `/v1/models` 接口实现

### utils/ - 工具模块
- `logger.py`: 统一的日志配置

## 优势

1. **模块化**: 每个模块职责单一，便于维护
2. **可测试**: 各模块可独立测试
3. **可扩展**: 新增功能只需添加对应模块
4. **代码复用**: 公共逻辑抽取到独立模块
5. **清晰的依赖关系**: 模块间依赖关系明确

## 迁移说明

- 旧的 `app.py` 已备份为 `app_old.py`
- 新的模块化代码完全兼容原有功能
- 配置文件 `config.json` 无需修改
