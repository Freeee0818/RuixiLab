/**
 * PySR参数管理 Composable
 * 管理PySR和神经网络的参数配置
 */

import { ref, reactive, computed, watch } from 'vue'

export function usePySRParameters() {
  // 算法选择
  const formulaAlgorithm = ref('pysr')
  
  // 运算符选择
  const binary_add = ref(true)
  const binary_subtract = ref(true)
  const binary_multiply = ref(true)
  const binary_divide = ref(true)
  
  const unaryOperators = ref([
    { name: 'exp', label: '指数', symbol: 'exp', enabled: true, complexity: 1 },
    { name: 'log', label: '对数', symbol: 'log', enabled: true, complexity: 1 },
    { name: 'sin', label: '正弦', symbol: 'sin', enabled: true, complexity: 1 },
    { name: 'cos', label: '余弦', symbol: 'cos', enabled: true, complexity: 1 }
  ])
  
  // 计算属性 - 运算符列表
  const binary_operators = computed(() => {
    const operators = []
    if (binary_add.value) operators.push('+')
    if (binary_subtract.value) operators.push('-')
    if (binary_multiply.value) operators.push('*')
    if (binary_divide.value) operators.push('/')
    return operators
  })
  
  const unary_operators = computed(() => {
    return unaryOperators.value
      .filter(op => op.enabled)
      .map(op => op.name)
  })
  
  const complexity_of_operators = computed(() => {
    const complexities = {}
    // 二元运算符复杂度
    if (binary_add.value) complexities['+'] = 1
    if (binary_subtract.value) complexities['-'] = 1
    if (binary_multiply.value) complexities['*'] = 1
    if (binary_divide.value) complexities['/'] = 1
    
    // 一元运算符复杂度
    unaryOperators.value
      .filter(op => op.enabled)
      .forEach(op => {
        complexities[op.name] = op.complexity
      })
    
    return complexities
  })
  
  // PySR参数
  const pysrParameters = reactive({
    population_size: 20,
    niterations: 100,
    maxsize: 20,
    binary_operators: ['+', '-', '*', '/'],
    unary_operators: ['exp', 'log', 'sin', 'cos'],
    complexity_of_operators: {},
    algorithm: 'pysr'
  })
  
  // 神经网络参数
  const neuralParameters = reactive({
    algorithm: 'neural_network',
    hidden_layers: 2,
    neurons_per_layer: 64,
    activation: 'relu',
    learning_rate: 0.001,
    epochs: 500,
    batch_size: 32,
    optimizer: 'adam',
    regularization: 0
  })
  
  // 监听运算符变化，更新参数
  watch([binary_operators, unary_operators, complexity_of_operators], () => {
    pysrParameters.binary_operators = binary_operators.value
    pysrParameters.unary_operators = unary_operators.value
    pysrParameters.complexity_of_operators = complexity_of_operators.value
  })
  
  watch(formulaAlgorithm, (value) => {
    if (value === 'pysr') {
      pysrParameters.algorithm = value
    } else {
      neuralParameters.algorithm = value
    }
  })
  
  // 更新运算符复杂度
  const updateOperatorComplexity = () => {
    pysrParameters.complexity_of_operators = complexity_of_operators.value
  }
  
  // 获取当前算法的参数
  const getCurrentParameters = () => {
    return formulaAlgorithm.value === 'pysr' ? pysrParameters : neuralParameters
  }
  
  return {
    // 算法选择
    formulaAlgorithm,
    
    // 运算符
    binary_add,
    binary_subtract,
    binary_multiply,
    binary_divide,
    unaryOperators,
    
    // 计算属性
    binary_operators,
    unary_operators,
    complexity_of_operators,
    
    // 参数对象
    pysrParameters,
    neuralParameters,
    
    // 方法
    updateOperatorComplexity,
    getCurrentParameters,
  }
}

