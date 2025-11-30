#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PySR Service API - 使用FastAPI提供符号回归服务的REST API
使用Deepseek API
"""

import os
import sys
import tempfile
from typing import Dict, List, Any, Optional
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import json
import httpx
import asyncio
from bs4 import BeautifulSoup

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置和日志
from config import get_config
from config.logging_config import setup_logging

# 导入PySR服务
from pysr_service import service, create_regression_task, start_regression_task, get_task_status, list_all_tasks

# 设置日志
logger = setup_logging()
config = get_config()

# 创建FastAPI应用
app = FastAPI(
    title="Symbolic Regression API",
    description="API for performing symbolic regression using PySR",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS if config.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI助手相关模型
class ExperimentInput(BaseModel):
    background: Optional[str] = ""
    data_description: Optional[str] = ""
    question: str
    formula: Optional[str] = ""
    plot_image: Optional[str] = ""  # 添加图片字段
    conversation_id: Optional[str] = None  # 会话ID，用于上下文记忆
    reset_context: Optional[bool] = False  # 是否清空该会话历史

class AssistantResponse(BaseModel):
    analysis: str
    suggestions: List[str]

# 获取AI API配置
try:
    API_CONFIG = config.get_ai_config()
    DEEPSEEK_API_BASE = API_CONFIG["base_url"]
    DEEPSEEK_API_KEY = API_CONFIG["api_key"]
    MODEL_NAME = API_CONFIG["model"]
    logger.info(f"AI API配置加载成功: {MODEL_NAME} @ {DEEPSEEK_API_BASE}")
except ValueError as e:
    logger.warning(f"AI API配置未加载: {e}")
    DEEPSEEK_API_BASE = ""
    DEEPSEEK_API_KEY = ""
    MODEL_NAME = ""

# 更新系统提示
SYSTEM_PROMPT = """你是一个专业的物理实验助手。
我会提供实验背景、数据可视化或公式。请根据用户问题进行有的放矢的回答：
 - 必要时说明数据分布/趋势与物理含义；
 - 指出明显异常或不确定性来源；
 - 仅当用户明确要求或确有必要时，才给出“改进建议”。

请用简洁专业的语言作答。
务必使用纯文本与 $...$ 或 \[...\] 的 LaTeX 公式；不要输出表格/图片/HTML 环境；尽量将单位与变量放在同一行。"""

# 定义API路由
@app.get("/")
async def root():
    """API根端点"""
    return {"message": "Symbolic Regression API is running"}

@app.post("/api/tasks")
async def submit_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    params: Optional[str] = Form("{}")
):
    """创建新的符号回归任务"""
    try:
        # 将上传的文件保存到临时目录
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        # 解析参数
        try:
            parameters = json.loads(params)
        except json.JSONDecodeError:
            parameters = {}
        
        # 创建任务
        task_id = service.create_task(file_path, parameters)
        
        # 在后台启动任务
        background_tasks.add_task(start_regression_task, task_id)
        
        return {"task_id": task_id}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务状态"""
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/api/tasks")
async def list_tasks():
    """列出所有任务"""
    return {"tasks": service.list_tasks()}

@app.post("/analyze_experiment")
@app.post("/api/analyze_experiment")
async def analyze_experiment(input_data: ExperimentInput):
    """分析实验数据"""
    try:
        # 构建更详细的提示
        context = []
        if input_data.background.strip():
            context.append(f"实验背景：{input_data.background}")
        if input_data.data_description.strip():
            context.append(f"数据说明：{input_data.data_description}")
        if input_data.formula.strip():
            context.append(f"相关公式：{input_data.formula}")
        if input_data.plot_image:
            context.append("数据可视化图表已提供，请基于图表进行分析。")
        
        context_text = "\n".join(context) if context else "无背景信息"
        
        # 简易会话内存：按 conversation_id 聚合
        conv_id = input_data.conversation_id or "default"
        if not hasattr(app.state, 'conversations'):
            app.state.conversations = {}
        if input_data.reset_context:
            app.state.conversations.pop(conv_id, None)
        history = app.state.conversations.get(conv_id, [])

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [
            {"role": "user", "content": f"{context_text}\n\n问题：{input_data.question}\n\n请根据提供的信息进行分析。"}
        ]
        
        request_data = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": API_CONFIG["max_tokens"],
            "stream": True
        }

        async def generate_stream():
            logger.info("开始生成流式响应...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    # 检查API Key是否配置
                    if not DEEPSEEK_API_KEY:
                        logger.error("AI API密钥未配置")
                        yield f"data: {json.dumps({'type':'error','message':'未配置AI服务密钥。请设置AI_API_KEY或SCHOOL_API_KEY环境变量后重试。'})}\n\n"
                        return
                    response = await client.post(
                        f"{DEEPSEEK_API_BASE}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                            "Content-Type": "application/json",
                            "Accept": "text/event-stream"
                        },
                        json=request_data,
                        timeout=30.0
                    )
                    
                    if response.status_code == 401:
                        yield f"data: {json.dumps({'type':'error','message':'AI服务认证失败(401)。请检查密钥是否正确/有效。'})}\n\n"
                        return
                    response.raise_for_status()
                    logger.debug("API请求成功，开始接收流式数据...")
                    
                    async for line in response.aiter_lines():
                        logger.debug(f"收到原始行: {line}")
                        if not line.strip():
                            continue
                            
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                # print(f"解析后的数据: {data}")
                                
                                if data.get("choices") and len(data["choices"]) > 0:
                                    choice = data["choices"][0]
                                    # 兼容不同API的delta结构
                                    content = ""
                                    if "delta" in choice and "content" in choice["delta"]:
                                        content = choice["delta"]["content"]
                                    elif "message" in choice and "content" in choice["message"]:
                                        content = choice["message"]["content"]
                                    # 只要有内容就yield
                                    if content:
                                        # print(f"发送内容: {content}")
                                        yield f"data: {json.dumps({'content': content})}\n\n"
                                    # 结束信号
                                    if choice.get("finish_reason") == "stop" or choice.get("stop_reason") == "stop":
                                        # print("收到结束标记")
                                        break
                                # 兼容 usage 统计chunk和空choices
                                elif "usage" in data:
                                    # 跳过
                                    continue
                                
                            except json.JSONDecodeError as e:
                                # print(f"JSON解析错误: {e}, 原始行: {line}")
                                continue
                                
                except Exception as e:
                    logger.error(f"流式处理错误: {str(e)}", exc_info=True)
                    yield f"data: {json.dumps({'type':'error','message':'AI服务暂时不可用或网络异常，请稍后再试。'})}\n\n"
                    return

        # 将本轮用户与助手消息追加到会话历史（只保留最近若干条以防爆内存）
        if not hasattr(app.state, 'conversations'):
            app.state.conversations = {}
        conv_id = getattr(input_data, 'conversation_id', None) or 'default'
        history = app.state.conversations.get(conv_id, [])
        # 仅在非流式阶段统一追加“用户问 + 助手答占位”，前端接收完可再触发保存完整答案
        if len(history) > 16:
            history = history[-16:]
        app.state.conversations[conv_id] = history

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用Nginx缓冲
            }
        )
        
    except Exception as e:
        logger.error(f"服务器错误: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "服务器遇到了错误，请稍后重试。"}
        )

# 主函数
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='PySR REST API')
    parser.add_argument('--host', type=str, default="0.0.0.0", help='Host to run the API on')
    parser.add_argument('--port', type=int, default=8000, help='Port to run the API on')
    args = parser.parse_args()
    
    # 启动FastAPI应用
    uvicorn.run(app, host=args.host, port=args.port)