/**
 * 数据分析服务API
 * 提供数据可视化和统计分析功能
 */

import { createServiceClient } from '../http'
import { API_SERVICES, API_ENDPOINTS } from '../config'

// 创建数据分析服务客户端
const client = createServiceClient(API_SERVICES.ANALYSIS)

/**
 * 数据分析服务API集合
 */
export const analysisAPI = {
  /**
   * 分析数据并生成可视化图表
   * @param {File} file - 数据文件
   * @param {Object} params - 可视化参数
   * @param {string} params.chartType - 图表类型：scatter/line/bar/box/heatmap
   * @param {Object} params.options - 图表选项
   * @param {string} [params.options.title] - 图表标题
   * @param {string} [params.options.xLabel] - X轴标签
   * @param {string} [params.options.yLabel] - Y轴标签
   * @param {boolean} [params.options.showGrid] - 是否显示网格
   * @param {boolean} [params.options.showTrendline] - 是否显示趋势线（散点图）
   * @returns {Promise<Object>} 分析结果
   * @returns {boolean} return.success - 是否成功
   * @returns {string} return.plot - 图表的base64编码
   * @returns {string} return.analysis - 分析文本结果
   */
  async analyzeData(file, params) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('params', JSON.stringify(params))

    return client.post(API_ENDPOINTS.ANALYSIS.ANALYZE_DATA, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  /**
   * 预定义的图表配置
   */
  chartConfigs: {
    /**
     * 散点图配置
     * @param {Object} options - 自定义选项
     * @returns {Object} 图表参数
     */
    scatter(options = {}) {
      return {
        chartType: 'scatter',
        options: {
          title: options.title || '散点图',
          xLabel: options.xLabel || 'X',
          yLabel: options.yLabel || 'Y',
          showGrid: options.showGrid !== false,
          showTrendline: options.showTrendline || false,
        },
      }
    },

    /**
     * 折线图配置
     * @param {Object} options - 自定义选项
     * @returns {Object} 图表参数
     */
    line(options = {}) {
      return {
        chartType: 'line',
        options: {
          title: options.title || '折线图',
          xLabel: options.xLabel || 'X',
          yLabel: options.yLabel || 'Y',
          showGrid: options.showGrid !== false,
        },
      }
    },

    /**
     * 柱状图配置
     * @param {Object} options - 自定义选项
     * @returns {Object} 图表参数
     */
    bar(options = {}) {
      return {
        chartType: 'bar',
        options: {
          title: options.title || '柱状图',
          xLabel: options.xLabel || 'X',
          yLabel: options.yLabel || 'Y',
          showGrid: options.showGrid !== false,
        },
      }
    },

    /**
     * 箱线图配置
     * @param {Object} options - 自定义选项
     * @returns {Object} 图表参数
     */
    box(options = {}) {
      return {
        chartType: 'box',
        options: {
          title: options.title || '箱线图',
          xLabel: options.xLabel || '',
          yLabel: options.yLabel || 'Y',
          showGrid: options.showGrid !== false,
        },
      }
    },

    /**
     * 热力图配置
     * @param {Object} options - 自定义选项
     * @returns {Object} 图表参数
     */
    heatmap(options = {}) {
      return {
        chartType: 'heatmap',
        options: {
          title: options.title || '相关性热力图',
          xLabel: options.xLabel || '',
          yLabel: options.yLabel || '',
          showGrid: options.showGrid !== false,
        },
      }
    },
  },
}

export default analysisAPI

