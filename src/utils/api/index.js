/**
 * API模块统一入口
 * 导出所有服务API和配置
 */

// 导出服务API
export { pysrAPI } from './services/pysr'
export { analysisAPI } from './services/analysis'

// 导出配置（供需要的地方使用）
export { API_SERVICES, API_ENDPOINTS } from './config'

// 导出HTTP客户端工具（供自定义请求使用）
export { createServiceClient, createSilentClient } from './http'

/**
 * 使用示例：
 *
 * import { pysrAPI, analysisAPI } from '@/utils/api'
 *
 * // PySR服务
 * const result = await pysrAPI.submitTask(file, params)
 * const status = await pysrAPI.getTaskStatus(taskId)
 * await pysrAPI.pollTaskStatus(taskId, (info, progress) => {
 *   console.log('进度:', progress)
 * })
 *
 * // 数据分析服务
 * const analysis = await analysisAPI.analyzeData(file,
 *   analysisAPI.chartConfigs.scatter({ title: '我的散点图' })
 * )
 */

