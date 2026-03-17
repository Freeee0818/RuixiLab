import os
import sys
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import json
import logging
from typing import Optional
from scipy import stats

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置
from config import settings

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=f"{settings.APP_NAME} - Data Analysis API",
    description="API for data visualization and statistical analysis",
    version=settings.APP_VERSION
)

# 配置CORS - 使用配置文件中的设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

def validate_data(df: pd.DataFrame) -> bool:
    """验证数据是否有效"""
    # 检查是否至少有两列数据
    if df.shape[1] < 2:
        raise ValueError("数据文件必须至少包含两列数据")
    
    # 检查数据是否为数值型
    if not all(df.dtypes.apply(lambda x: np.issubdtype(x, np.number))):
        raise ValueError("所有列必须为数值类型")
    
    # 检查是否有空值
    if df.isnull().any().any():
        raise ValueError("数据中包含空值")
    
    return True

def create_plot(df: pd.DataFrame, params: dict) -> tuple[str, str]:
    """创建图表并返回base64编码的图像和分析结果"""
    try:
        plt.figure(figsize=(10, 6))
        plt.clf()  # 清除之前的图形
        
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 设置基本样式
        plt.style.use('default')  # 使用默认样式
        plt.grid(params['options']['showGrid'])  # 根据选项显示网格
        
        # 设置标题和标签
        if params['options']['title']:
            plt.title(params['options']['title'])
        if params['options']['xLabel']:
            plt.xlabel(params['options']['xLabel'])
        if params['options']['yLabel']:
            plt.ylabel(params['options']['yLabel'])
        
        x = df.iloc[:, 0]
        y = df.iloc[:, 1]
        analysis_text = ""
        
        logger.info(f"Creating {params['chartType']} plot")
        
        # 根据图表类型绘制
        if params['chartType'] == 'scatter':
            plt.scatter(x, y, alpha=0.6, c='#1f77b4', s=50)  # 使用好看的蓝色
            if params['options']['showTrendline']:
                z = np.polyfit(x, y, 1)
                p = np.poly1d(z)
                plt.plot(x, p(x), "r--", alpha=0.8, label=f'y = {z[0]:.4f}x + {z[1]:.4f}')
                plt.legend()
            
            # 计算相关系数
            correlation = stats.pearsonr(x, y)
            analysis_text = f"数据分析结果：\n"
            analysis_text += f"1. 数据点数量：{len(x)}\n"
            analysis_text += f"2. 相关系数：{correlation[0]:.4f} (p值：{correlation[1]:.4f})\n"
            analysis_text += f"3. X轴范围：{x.min():.4f} 到 {x.max():.4f}\n"
            analysis_text += f"4. Y轴范围：{y.min():.4f} 到 {y.max():.4f}\n"
            
        elif params['chartType'] == 'line':
            plt.plot(x, y, '-', color='#1f77b4', linewidth=2, alpha=0.8)
            plt.scatter(x, y, color='#1f77b4', alpha=0.6, s=30)
            
            # 计算趋势
            analysis_text = f"数据分析结果：\n"
            analysis_text += f"1. 数据点数量：{len(x)}\n"
            analysis_text += f"2. Y值变化范围：{y.min():.4f} 到 {y.max():.4f}\n"
            analysis_text += f"3. 平均斜率：{((y.iloc[-1] - y.iloc[0]) / (x.iloc[-1] - x.iloc[0])):.4f}\n"
            
        elif params['chartType'] == 'bar':
            plt.bar(x, y, alpha=0.6, color='#1f77b4')
            
            analysis_text = f"数据分析结果：\n"
            analysis_text += f"1. 数据点数量：{len(x)}\n"
            analysis_text += f"2. 总和：{y.sum():.4f}\n"
            analysis_text += f"3. 平均值：{y.mean():.4f}\n"
            analysis_text += f"4. 标准差：{y.std():.4f}\n"
            
        elif params['chartType'] == 'box':
            plt.boxplot(y, patch_artist=True)
            
            q1 = y.quantile(0.25)
            q3 = y.quantile(0.75)
            iqr = q3 - q1
            
            analysis_text = f"数据分析结果：\n"
            analysis_text += f"1. 中位数：{y.median():.4f}\n"
            analysis_text += f"2. 第一四分位数(Q1)：{q1:.4f}\n"
            analysis_text += f"3. 第三四分位数(Q3)：{q3:.4f}\n"
            analysis_text += f"4. 四分位距(IQR)：{iqr:.4f}\n"
            analysis_text += f"5. 异常值数量：{len(y[(y < (q1 - 1.5 * iqr)) | (y > (q3 + 1.5 * iqr))])}\n"
            
        elif params['chartType'] == 'heatmap':
            # 计算相关性矩阵
            corr_matrix = df.corr()
            sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, 
                       square=True, fmt='.4f')
            
            analysis_text = f"数据分析结果：\n"
            analysis_text += f"1. 变量之间的相关性：\n"
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    analysis_text += f"   - {corr_matrix.columns[i]} 与 {corr_matrix.columns[j]}: {corr_matrix.iloc[i,j]:.4f}\n"
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图片到内存
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
        plt.close()
        
        # 转换为base64
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        return plot_base64, analysis_text
        
    except Exception as e:
        logger.error(f"Error creating plot: {str(e)}")
        raise

@app.post("/analyze_data")
async def analyze_data(
    file: UploadFile = File(...),
    params: str = Form(...)
):
    try:
        logger.info(f"Received file: {file.filename}")
        logger.info(f"Received params: {params}")
        
        # 读取文件
        content = await file.read()
        
        # 打印原始内容的前几行用于调试
        try:
            raw_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raw_content = content.decode('gbk')
        
        # 尝试直接解析数据
        data_lines = [line.strip().split() for line in raw_content.splitlines() if line.strip()]
        if data_lines:
            logger.info(f"First line split result: {data_lines[0]}")
            # 如果数据是两列的，直接构造DataFrame
            if all(len(line) == 2 for line in data_lines):
                x_values = [float(line[0]) for line in data_lines]
                y_values = [float(line[1]) for line in data_lines]
                df = pd.DataFrame({'x': x_values, 'y': y_values})
            else:
                # 如果分割结果不是两列，尝试其他分隔符
                try:
                    # 尝试以空格分隔符读取
                    df = pd.read_csv(io.StringIO(raw_content), 
                                   delim_whitespace=True,
                                   header=None,
                                   names=['x', 'y'])
                except Exception as e1:
                    logger.error(f"Space delimiter failed: {str(e1)}")
                    try:
                        # 尝试以逗号分隔符读取
                        df = pd.read_csv(io.StringIO(raw_content),
                                       header=None,
                                       names=['x', 'y'])
                    except Exception as e2:
                        logger.error(f"Comma delimiter failed: {str(e2)}")
                        # 如果都失败了，尝试制表符
                        df = pd.read_csv(io.StringIO(raw_content),
                                       sep='\t',
                                       header=None,
                                       names=['x', 'y'])
        
        logger.info(f"Data shape: {df.shape}")
        logger.info(f"Data columns: {df.columns.tolist()}")
        logger.info(f"First few rows: \n{df.head()}")
        
        # 验证数据
        validate_data(df)
        
        # 解析参数
        visualization_params = json.loads(params)
        
        # 创建图表
        plot_base64, analysis = create_plot(df, visualization_params)
        
        return {
            "success": True,
            "plot": plot_base64,
            "analysis": analysis
        }
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import argparse
    import uvicorn
    
    parser = argparse.ArgumentParser(description='Data Analysis REST API')
    parser.add_argument('--host', type=str, default=settings.ANALYSIS_SERVICE_HOST, help='Host to run the API on')
    parser.add_argument('--port', type=int, default=settings.ANALYSIS_SERVICE_PORT, help='Port to run the API on')
    args = parser.parse_args()
    
    print(f"\n🚀 启动 {settings.APP_NAME} 数据分析服务")
    print(f"📍 地址: http://{args.host}:{args.port}")
    print(f"📖 文档: http://{args.host}:{args.port}/docs")
    print(f"🔧 配置文件: .env\n")
    
    logger.info("Starting data analysis server...")
    uvicorn.run(app, host=args.host, port=args.port) 