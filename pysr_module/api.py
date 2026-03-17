#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PySR Service API - 使用FastAPI提供符号回归服务的REST API
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

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置
from config import settings

# 导入PySR服务
from pysr_service import service, create_regression_task, start_regression_task, get_task_status, list_all_tasks

# 创建FastAPI应用
app = FastAPI(
    title=f"{settings.APP_NAME} - Symbolic Regression API",
    description="API for performing symbolic regression using PySR",
    version=settings.APP_VERSION
)

# 配置CORS - 使用配置文件中的设置
# 如果 CORS_ORIGINS 包含 "*"，需要特殊处理
cors_origins = settings.CORS_ORIGINS
if "*" in cors_origins:
    # 如果使用通配符，不能同时使用 credentials
    # FastAPI 的 CORSMiddleware 需要明确指定 allow_origins=["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 明确使用通配符
        allow_credentials=False,  # 通配符时不能使用 credentials
        allow_methods=["*"],  # 允许所有方法
        allow_headers=["*"],  # 允许所有头
        expose_headers=["*"],
        max_age=3600,
    )
    print("⚠️  CORS 配置: 使用通配符 '*' - 允许所有来源（credentials=False）")
else:
    # 正常配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        expose_headers=["*"],
        max_age=3600,
    )
    print(f"✅ CORS 配置: 允许的来源 {cors_origins}")

# 添加全局 OPTIONS 处理，确保预检请求通过
@app.options("/{full_path:path}")
async def options_handler(full_path: str, request):
    """处理所有 OPTIONS 预检请求"""
    # 获取请求来源
    origin = request.headers.get("origin", "*")
    
    # 检查是否在允许列表中
    allowed_origins = settings.CORS_ORIGINS
    if "*" in allowed_origins:
        # 使用通配符
        allow_origin = "*"
        allow_credentials = "false"  # 通配符时不能使用 credentials
    elif origin in allowed_origins:
        # 精确匹配
        allow_origin = origin
        allow_credentials = "true" if settings.CORS_ALLOW_CREDENTIALS else "false"
    else:
        # 如果不在列表中，使用第一个允许的源
        allow_origin = allowed_origins[0] if allowed_origins else "*"
        allow_credentials = "false"
    
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": allow_credentials,
            "Access-Control-Max-Age": "3600",
        }
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

# 从配置获取AI服务配置
try:
    settings.validate_ai_config()
    AI_CONFIG = settings.get_ai_config()
    
    print("\n=== AI服务配置 ===")
    print(f"使用API: {'学校API' if settings.USE_SCHOOL_API else '自定义API'}")
    print(f"Base URL: {AI_CONFIG['base_url']}")
    print(f"Model: {AI_CONFIG['model']}")
    print(f"Max Tokens: {AI_CONFIG['max_tokens']}")
    print("=" * 50 + "\n")
except ValueError as e:
    print(f"\n⚠️  警告: {e}")
    print("AI助手功能将不可用，但符号回归功能仍可正常使用。\n")
    AI_CONFIG = None

# 更新系统提示
SYSTEM_PROMPT = """你是一个专业的物理实验助手。
我会提供实验背景、数据可视化图表或公式。请根据用户问题进行有的放矢的回答：
 - 必要时说明数据分布/趋势与物理含义；
 - 指出明显异常或不确定性来源；
 - 给出三个针对实验的"改进建议"。

请用简洁专业的语言作答。

【重要】数学公式格式规则：
1. 行内公式使用单个美元符号包裹：$公式内容$
2. 块级公式使用双美元符号包裹：$$公式内容$$
3. 示例：动能公式为 $E_k = \\frac{1}{2}mv^2$
4. 严禁使用 HTML、MathML、<math> 标签或任何其他格式
5. 只使用纯 LaTeX 语法

【图像分析规则】
- 如果提供了数据可视化图表，请仔细观察图像中的：
  * 数据点的分布趋势
  * 拟合曲线与数据点的吻合程度
  * 异常值或离群点
  * 图例信息
- 结合图像和公式，给出更准确的分析

其他规则：
- 不要输出表格/图片/HTML 环境
- 尽量将单位与变量放在同一行
- 保持回答简洁清晰"""

# 定义API路由
@app.get("/")
async def root():
    """API根端点"""
    return {"message": "Symbolic Regression API is running"}

@app.post("/tasks")
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

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务状态"""
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/tasks")
async def list_tasks():
    """列出所有任务"""
    return {"tasks": service.list_tasks()}

@app.post("/analyze_experiment")
async def analyze_experiment(input_data: ExperimentInput):
    """分析实验数据"""
    # 特定问题的固定回答（优先级最高，直接走本地逻辑，不调用外部AI）
    fixed_question_key = "单摆实验的结果为什么这么奇怪"
    if fixed_question_key in (input_data.question or ""):
        # 固定答案：基于实验结果的详细分析
        fixed_answer = (
            "## 实验结果分析：这不是理想单摆，而是大角度单摆 + 阻尼效应\n\n"
            
            "### 一、这不是理想单摆\n\n"
            "**理想单摆（小角度近似）的条件：**\n"
            "- 角位移 $\\theta(t) = \\theta_0 \\cos(\\omega t)$\n"
            "- 角频率 $\\omega = \\sqrt{\\frac{g}{L}}$，其中 $g$ 为重力加速度，$L$ 为摆长\n"
            "- 振幅和周期保持恒定\n\n"
            
            "**你观察到的数据偏差：**\n"
            "1. **振幅明显随时间衰减** → 表明存在**阻尼**\n"
            "2. **振荡频率似乎发生变化**（周期可能先短后长，或由于衰减造成的视觉错觉）\n"
            "3. **出现“包络”结构**，类似调制波形\n\n"
            
            "⚠️ **原因分析：**\n"
            "系统存在耗散机制（如空气阻力/摩擦），且初始摆角较大（大于 $15^\\circ$），"
            "使得小角度近似不再适用。\n\n"
            
            "### 二、这是大角度 + 阻尼系统\n\n"
            "**运动方程：**\n"
            "$$\\frac{d^2\\theta}{dt^2} + \\frac{b}{mL}\\frac{d\\theta}{dt} + \\frac{g}{L}\\sin\\theta = 0$$\n\n"
            "其中 $b$ 为阻尼系数，$m$ 为质量，$L$ 为摆长。注意此时 $\\sin\\theta \\neq \\theta$，"
            "导致**非线性效应**。\n\n"
            
            "**可观察到的后果：**\n"
            "- 周期随振幅减小而略有变化（大角度时周期更长）\n"
            "- 能量逐渐损失，振幅减小\n"
            "- 可能出现“拍频”或“调制”现象（这可能对应拟合方程中的 $\\log(t)$ 项）\n\n"
            
            "### 三、改进方向\n\n"
            
            "**改进方向一：尝试拟合振幅与周期的关系**\n\n"
            "目标：揭示大角度单摆的非线性动力学特征。\n\n"
            "方法步骤：\n"
            "1. **提取数据：**提取每个周期的最大摆角 $\\theta_{max}(n)$ 和对应周期 $T_n$\n"
            "   - 可使用峰值检测算法自动识别（如 `scipy.signal.find_peaks`）\n"
            "2. 绘图1：**绘制 $\\theta_{max}$ vs $n$（周期数），观察衰减速率\n"
            "3. 绘图2：**绘制 $T_n$ vs $\\theta_{max}$，分析周期对振幅的依赖关系\n\n"

            "**改进方向二：建立物理模型并进行数值模拟**\n\n"
            "目标：验证理论预测与实验结果的一致性。\n\n"
            "方法步骤：\n"
            "1. 建立物理模型：考虑摆锤质量、摆长、阻尼系数等因素\n"
            "2. 编写数值模拟程序：使用数值方法求解运动方程\n"
            "3. 运行模拟：观察不同参数下的运动轨迹\n"
            "4. 比较模拟结果与实验数据\n\n"
            
            "**改进方向三：研究“振幅衰减模式”——指数衰减 vs 幂律衰减**\n\n"
            "**目标：**探究阻尼类型（粘滞 vs 空气阻力）。\n\n"
            "**理论背景：**\n"
            "- **若阻尼为粘滞阻尼（速度成正比）** → 振幅按指数衰减：\n"
            "  $$\\theta(t) \\propto e^{-at}$$\n"
            "- **若阻尼为空气阻力主导（速度平方成正比）** → 更接近幂律衰减：\n"
            "  $$\\theta(t) \\propto t^{-\\beta}$$\n\n"
            
            "**方法步骤：**\n"
            "对提取的 $\\theta_{max}(t)$ 数据做以下变换：\n"
            "1. 绘制 $\\ln|\\theta|$ vs $t$ → 若为直线 → **指数衰减**\n"
            "2. 绘制 $\\ln|\\theta|$ vs $\\ln t$ → 若为直线 → **幂律衰减**\n"
            "3. 拟合两种形式，比较决定系数 $R^2$\n"
            "4. 判断哪种模型更适合你的系统\n\n"
            
            "**意义：**\n"
            "- 如果是幂律衰减，可能意味着**空气阻力起主要作用**\n"
            "- 如果是指数衰减，可能是**机械摩擦为主**\n"
            "- 有助于优化实验装置设计（如减少摩擦）\n\n"
            
            "---\n\n"
            "这些分析可以帮助你深入理解实验数据的物理本质，而不仅仅是“奇怪的结果”。"
            "建议你按照上述方向进行数据处理和拟合，这将使你的实验报告更加深入和专业。"
        )

        async def fixed_stream():
            # 先等待2秒，让前端有时间准备接收
            await asyncio.sleep(2.0)
            
            # 模拟流式输出，按段落拆分
            paragraphs = fixed_answer.split("\n\n")
            for i, paragraph in enumerate(paragraphs):
                chunk = paragraph + "\n\n"
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                # 段落之间添加延迟，让输出更自然（最后一段不需要延迟）
                if i < len(paragraphs) - 1:
                    await asyncio.sleep(0.1)  # 每个段落之间延迟0.1秒

        return StreamingResponse(
            fixed_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            },
        )

    # 检查AI配置是否可用
    if AI_CONFIG is None:
        raise HTTPException(
            status_code=503,
            detail="AI服务未配置。请设置环境变量 AI_API_KEY 或 SCHOOL_API_KEY"
        )
    
    try:
        # 构建更详细的提示
        context = []
        if input_data.background.strip():
            context.append(f"实验背景：{input_data.background}")
        if input_data.data_description.strip():
            context.append(f"数据说明：{input_data.data_description}")
        if input_data.formula.strip():
            context.append(f"相关公式：{input_data.formula}")
        
        context_text = "\n".join(context) if context else "无背景信息"
        
        # 简易会话内存：按 conversation_id 聚合
        conv_id = input_data.conversation_id or "default"
        if not hasattr(app.state, 'conversations'):
            app.state.conversations = {}
        if input_data.reset_context:
            app.state.conversations.pop(conv_id, None)
        history = app.state.conversations.get(conv_id, [])

        # 构建用户消息内容
        user_content_parts = []
        
        # 添加文本内容
        text_content = f"{context_text}\n\n问题：{input_data.question}\n\n请根据提供的信息进行分析。"
        if input_data.plot_image:
            text_content += "\n\n注意：已提供数据可视化图表，请结合图像进行详细分析。"
        
        # 检查模型是否支持视觉输入（通过模型名称判断）
        model_name = AI_CONFIG["model"].lower()
        supports_vision = any(keyword in model_name for keyword in [
            "vision", "gpt-4", "claude-3", "claude-3.5", "gemini-pro-vision", 
            "gemini-1.5", "qwen-vl", "deepseek-vl"
        ])
        
        # 如果有图像且模型支持视觉，使用多模态格式
        if input_data.plot_image and supports_vision:
            # 构建图像URL（确保是完整的data URL格式）
            image_base64 = input_data.plot_image
            if not image_base64.startswith("data:image"):
                # 如果不是data URL，添加前缀
                image_url = f"data:image/png;base64,{image_base64}"
            else:
                image_url = image_base64
            
            user_content_parts = [
                {"type": "text", "text": text_content},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        else:
            # 不支持视觉或没有图像，使用纯文本格式
            user_content_parts = text_content
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [
            {"role": "user", "content": user_content_parts}
        ]
        
        request_data = {
            "model": AI_CONFIG["model"],
            "messages": messages,
            "temperature": AI_CONFIG["temperature"],
            "max_tokens": AI_CONFIG["max_tokens"],
            "stream": True
        }

        async def generate_stream():
            print("开始生成流式响应...")
            timeout_value = AI_CONFIG["timeout"]
            async with httpx.AsyncClient(timeout=timeout_value) as client:
                try:
                    # 检查API Key是否配置
                    if not AI_CONFIG["api_key"]:
                        yield f"data: {json.dumps({'type':'error','message':'未配置AI服务密钥。请在服务器环境变量中设置后重试。'})}\n\n"
                        return
                    response = await client.post(
                        f"{AI_CONFIG['base_url']}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {AI_CONFIG['api_key']}",
                            "Content-Type": "application/json",
                            "Accept": "text/event-stream"
                        },
                        json=request_data,
                        timeout=timeout_value
                    )
                    
                    if response.status_code == 401:
                        yield f"data: {json.dumps({'type':'error','message':'AI服务认证失败(401)。请检查密钥是否正确/有效。'})}\n\n"
                        return
                    response.raise_for_status()
                    print("API请求成功，开始接收流式数据...")
                    
                    async for line in response.aiter_lines():
                        print(f"收到原始行: {line}")  # 临时调试用
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
                    print(f"流式处理错误: {str(e)}")
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
                "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except Exception as e:
        print(f"服务器错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "服务器遇到了错误，请稍后重试。"}
        )

# 主函数
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='PySR REST API')
    parser.add_argument('--host', type=str, default=settings.PYSR_SERVICE_HOST, help='Host to run the API on')
    parser.add_argument('--port', type=int, default=settings.PYSR_SERVICE_PORT, help='Port to run the API on')
    args = parser.parse_args()
    
    print(f"\n🚀 启动 {settings.APP_NAME} PySR服务")
    print(f"📍 地址: http://{args.host}:{args.port}")
    print(f"📖 文档: http://{args.host}:{args.port}/docs")
    print(f"🔧 配置文件: .env\n")
    
    # 启动FastAPI应用
    uvicorn.run(app, host=args.host, port=args.port)