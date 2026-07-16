/**
 * PySR 参数管理。
 *
 * 运算符采用计算后端的统一默认值，前端只保留会影响计算规模的参数。
 */

import { reactive } from 'vue'

export function usePySRParameters() {
  const pysrParameters = reactive({
    population_size: 20,
    niterations: 100,
    maxsize: 20,
    algorithm: 'pysr',
  })

  const getCurrentParameters = () => pysrParameters

  return {
    pysrParameters,
    getCurrentParameters,
  }
}
