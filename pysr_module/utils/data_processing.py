#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据处理工具
"""

import numpy as np
import pandas as pd
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def process_data_file(file_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    处理数据文件，返回X和y
    
    Args:
        file_path: 数据文件路径
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: (X, y) 特征矩阵和目标向量
        
    Raises:
        ValueError: 如果文件格式不支持或数据格式不正确
    """
    # 根据文件扩展名选择读取方式
    if file_path.endswith('.csv'):
        data = pd.read_csv(file_path)
    elif file_path.endswith('.txt'):
        # 统一用正则空白分隔符，兼容空格和tab
        data = pd.read_csv(file_path, sep=r'\s+', engine='python', header=None)
    else:
        raise ValueError("不支持的文件格式，仅支持 .csv 和 .txt 文件")
    
    # 确保数据是数值型
    data = data.apply(pd.to_numeric, errors='coerce')
    # 移除包含NaN的行
    data = data.dropna()
    
    if data.shape[1] < 2:
        raise ValueError("数据文件必须包含至少两列")
        
    # 返回处理后的X和y
    # 支持多X列：将最后一列作为y，其余列作为X
    if data.shape[1] == 2:
        X = data.iloc[:, 0].values.reshape(-1, 1)
        y = data.iloc[:, 1].values
    else:
        X = data.iloc[:, :-1].values
        y = data.iloc[:, -1].values
    
    logger.info(f"成功处理数据文件: {file_path}, 形状: X={X.shape}, y={y.shape}")
    return X, y





