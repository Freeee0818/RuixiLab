import os
import asyncio
import threading
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import json
import logging
from scipy import stats

# 导入配置
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])
_PLOT_LOCK = threading.Lock()

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


def parse_numeric_table(raw_content: str) -> pd.DataFrame:
    """Parse comma, tab, or whitespace-delimited numeric tables.

    Reading with ``header=None`` keeps header detection deterministic; textual
    header rows are removed by numeric coercion instead of becoming data.
    """
    attempts = (
        {"sep": None, "engine": "python", "header": None},
        {"sep": r"\s+", "engine": "python", "header": None},
        {"sep": ",", "header": None},
        {"sep": "\t", "header": None},
    )
    for options in attempts:
        try:
            frame = pd.read_csv(io.StringIO(raw_content), **options)
        except Exception:
            continue

        numeric = frame.apply(pd.to_numeric, errors="coerce")
        numeric = numeric.dropna(axis=1, how="all").dropna(axis=0, how="any")
        if numeric.shape[0] > 0 and numeric.shape[1] >= 2:
            numeric.columns = [f"column_{index + 1}" for index in range(numeric.shape[1])]
            return numeric.reset_index(drop=True)

    raise ValueError("无法解析数值表格，请使用逗号、空格或 Tab 分隔，并至少提供两列数据")

def create_plot(df: pd.DataFrame, params: dict) -> tuple[str, str]:
    """Serialize Matplotlib work while allowing the async API to stay responsive."""
    with _PLOT_LOCK:
        return _create_plot(df, params)


def _create_plot(df: pd.DataFrame, params: dict) -> tuple[str, str]:
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

@router.post("/analyze_data")
async def analyze_data(
    file: UploadFile = File(...),
    params: str = Form(...)
):
    try:
        logger.info(f"Received file: {file.filename}")
        logger.info(f"Received params: {params}")

        suffix = os.path.splitext(file.filename or "")[1].lower()
        if suffix not in {".csv", ".txt"}:
            raise ValueError("仅支持 .csv 和 .txt 数据文件")
        
        # 读取文件
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大允许 {settings.MAX_FILE_SIZE // (1024 * 1024)} MB",
            )
        
        # 打印原始内容的前几行用于调试
        try:
            raw_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raw_content = content.decode('gbk')
        
        if not raw_content.strip():
            raise ValueError("数据文件为空")
        df = parse_numeric_table(raw_content)
        
        logger.info(f"Data shape: {df.shape}")
        logger.info(f"Data columns: {df.columns.tolist()}")
        logger.info(f"First few rows: \n{df.head()}")
        
        # 验证数据
        validate_data(df)
        
        # 解析参数
        visualization_params = json.loads(params)
        
        # 创建图表
        plot_base64, analysis = await asyncio.to_thread(create_plot, df, visualization_params)
        
        return {
            "success": True,
            "plot": plot_base64,
            "analysis": analysis
        }
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
