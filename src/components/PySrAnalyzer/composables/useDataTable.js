/**
 * 数据表格管理 Composable
 * 处理表格数据的增删改查、验证、导入导出等操作
 */

import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

export function useDataTable() {
  // 表格数据
  const tableData = ref([])
  const tableColumns = ref([
    { prop: 'col0', label: '第1列' },
    { prop: 'col1', label: '第2列' }
  ])
  
  // X和Y列选择
  const selectedXCols = ref([0])
  const selectedYCol = ref(1)
  
  // 行分页
  const rowGroupSize = 21
  const rowGroupIndex = ref(0)
  const totalRowsDesired = ref(0)
  
  // 计算属性
  const rowGroupOptions = computed(() => {
    const total = tableData.value.length
    const groups = Math.max(1, Math.ceil(total / rowGroupSize))
    return Array.from({ length: groups }, (_, i) => ({
      value: i,
      label: `第 ${i * rowGroupSize + 1} - ${Math.min((i + 1) * rowGroupSize, total)} 行`
    }))
  })
  
  const visibleRows = computed(() => {
    const start = rowGroupIndex.value * rowGroupSize
    const end = start + rowGroupSize
    return tableData.value.slice(start, end)
  })
  
  const availableTableCols = computed(() =>
    tableColumns.value.map((col, index) => ({
      value: index,
      label: col.label
    }))
  )
  
  const canUseTable = computed(() => {
    if (tableData.value.length === 0) return false
    if (!Array.isArray(selectedXCols.value) || selectedXCols.value.length === 0) return false
    if (selectedXCols.value.includes(selectedYCol.value)) return false
    return tableData.value.some(row => {
      const xsValid = selectedXCols.value.every(idx => Number.isFinite(Number(row[`col${idx}`])))
      const y = Number(row[`col${selectedYCol.value}`])
      return xsValid && Number.isFinite(y)
    })
  })
  
  // 方法：加载文件
  const loadDataFile = () => {
    return new Promise((resolve, reject) => {
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = '.csv,.txt'
      input.style.display = 'none'
      
      input.onchange = async (event) => {
        try {
          const files = event.target.files
          if (files.length > 0) {
            const file = files[0]
            const text = await file.text()
            const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean)
            
            if (lines.length > 0) {
              parseDataLines(lines)
              useFirstRowAsHeader()
              resetColumnSelectors()
              rowGroupIndex.value = 0
              
              ElMessage.success(`已成功解析文件 ${file.name}，共 ${tableData.value.length} 行数据`)
              resolve(file)
            }
          }
        } catch (error) {
          console.error('解析文件失败:', error)
          ElMessage.error('文件解析失败，请检查文件格式')
          reject(error)
        } finally {
          document.body.removeChild(input)
        }
      }
      
      document.body.appendChild(input)
      input.click()
    })
  }
  
  // 解析数据行
  const parseDataLines = (lines) => {
    const parsedRows = lines.map(line => {
      const cells = line.split(/\s+|,|\t/).filter(Boolean)
      return cells
    })
    
    const maxCols = Math.max(...parsedRows.map(row => row.length))
    
    tableColumns.value = Array.from({ length: maxCols }, (_, i) => ({
      prop: `col${i}`,
      label: `第${i + 1}列`
    }))
    
    tableData.value = parsedRows.map(row => {
      const tableRow = {}
      tableColumns.value.forEach((col, index) => {
        tableRow[col.prop] = row[index] || ''
      })
      return tableRow
    })
  }
  
  // 使用第一行作为列名
  const useFirstRowAsHeader = () => {
    if (!tableData.value.length) return
    const firstRow = tableData.value[0]
    tableColumns.value = tableColumns.value.map((col, idx) => ({
      prop: col.prop,
      label: String(firstRow[col.prop] || `第${idx + 1}列`)
    }))
    tableData.value.splice(0, 1)
  }
  
  // 重置列选择器
  const resetColumnSelectors = () => {
    const maxCols = tableColumns.value.length
    selectedXCols.value = [0]
    selectedYCol.value = Math.min(1, maxCols - 1)
  }
  
  // 表格操作
  const addRow = () => {
    const newRow = {}
    tableColumns.value.forEach(col => {
      newRow[col.prop] = ''
    })
    tableData.value.push(newRow)
  }
  
  const addColumn = () => {
    const colIndex = tableColumns.value.length
    const newCol = {
      prop: `col${colIndex}`,
      label: `第${colIndex + 1}列`
    }
    tableColumns.value.push(newCol)
    
    tableData.value.forEach(row => {
      row[newCol.prop] = ''
    })
  }
  
  const deleteRow = (index) => {
    const actualIndex = rowGroupIndex.value * rowGroupSize + index
    tableData.value.splice(actualIndex, 1)
  }
  
  const clearTable = () => {
    tableData.value = []
    tableColumns.value = [
      { prop: 'col0', label: '第1列' },
      { prop: 'col1', label: '第2列' }
    ]
    selectedXCols.value = [0]
    selectedYCol.value = 1
    rowGroupIndex.value = 0
    totalRowsDesired.value = 0
  }
  
  // 加载示例数据
  const loadSampleData = async (sampleType = 'default') => {
    try {
      // 根据 sample 类型选择不同的数据文件
      let dataFile = '/单摆实验数据.txt'
      let successMessage = '已加载单摆实验示例数据'
      
      if (sampleType === 'large_angle_pendulum' || sampleType === 'pendulum') {
        dataFile = '/大角度摆周期vs摆幅.txt'
        successMessage = '已加载大角度单摆实验示例数据'
      }
      
      const response = await fetch(dataFile)
      if (!response.ok) {
        throw new Error('无法加载示例数据文件')
      }
      
      const text = await response.text()
      const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean)
      
      if (lines.length > 0) {
        parseDataLines(lines)
        useFirstRowAsHeader()
        resetColumnSelectors()
        rowGroupIndex.value = 0
        
        ElMessage.success(`${successMessage}，共 ${tableData.value.length} 行数据`)
      }
    } catch (error) {
      console.error('加载示例数据失败:', error)
      ElMessage.error('加载示例数据失败')
      
      // 备选数据
      const fallbackData = [
        { col0: '0.167', col1: '16.9' },
        { col0: '0.200', col1: '18.3' },
        { col0: '0.233', col1: '21.2' },
        { col0: '0.267', col1: '25.3' },
        { col0: '0.300', col1: '28.9' }
      ]
      tableData.value = fallbackData
      resetColumnSelectors()
      rowGroupIndex.value = 0
    }
  }
  
  // 验证单元格
  const validateCell = (row, prop) => {
    const value = row[prop]
    if (value && isNaN(Number(value))) {
      ElMessage.warning('请输入有效的数字')
    }
  }
  
  // 设置总行数
  const applyTotalRows = () => {
    const target = Math.max(1, Math.min(10000, Number(totalRowsDesired.value) || 0))
    if (target > tableData.value.length) {
      const need = target - tableData.value.length
      for (let i = 0; i < need; i++) addRow()
    } else if (target < tableData.value.length) {
      tableData.value.splice(target)
      rowGroupIndex.value = Math.min(rowGroupIndex.value, Math.floor((target - 1) / rowGroupSize))
    }
    totalRowsDesired.value = tableData.value.length
    ElMessage.success(`已设置总行数为 ${tableData.value.length}`)
  }
  
  // 从表格构建文件
  const buildBlobFromTable = () => {
    const lines = tableData.value
      .map(row => {
        const xValues = selectedXCols.value.map(idx => Number(row[`col${idx}`]))
        const y = Number(row[`col${selectedYCol.value}`])
        const xsValid = xValues.every(v => Number.isFinite(v))
        if (xsValid && Number.isFinite(y)) {
          return `${xValues.join('\t')}\t${y}`
        }
        return null
      })
      .filter(Boolean)
      .join('\n')
    const blob = new Blob([lines], { type: 'text/plain' })
    return new File([blob], 'table_data.txt', { type: 'text/plain' })
  }
  
  // 使用表格作为文件
  const useTableAsFile = () => {
    if (!canUseTable.value) return null
    const file = buildBlobFromTable()
    ElMessage.success('已使用表格数据作为当前文件')
    return file
  }
  
  // 变量映射文本
  const getVariableMappingText = () => {
    if (!Array.isArray(selectedXCols.value) || selectedXCols.value.length === 0) return ''
    const names = selectedXCols.value.map((idx, i) => 
      `${tableColumns.value[idx]?.label || `第${idx+1}列`}→x${i}`
    )
    const yName = tableColumns.value[selectedYCol.value]?.label || `第${selectedYCol.value+1}列`
    return `变量映射：${names.join('，')}；Y 为 ${yName}。方程中变量以 x0, x1, x2... 表示。`
  }
  
  // 获取变量映射对象
  const getVariableMapping = () => {
    return {
      x_variables: selectedXCols.value.map((colIndex, i) => ({
        index: i,
        name: tableColumns.value[colIndex]?.label || `col${colIndex}`,
        pysr_name: `x${i}`
      })),
      y_variable: {
        name: tableColumns.value[selectedYCol.value]?.label || `col${selectedYCol.value}`,
        pysr_name: 'y'
      }
    }
  }
  
  return {
    // 状态
    tableData,
    tableColumns,
    selectedXCols,
    selectedYCol,
    rowGroupIndex,
    rowGroupSize,
    totalRowsDesired,
    
    // 计算属性
    rowGroupOptions,
    visibleRows,
    availableTableCols,
    canUseTable,
    
    // 方法
    loadDataFile,
    loadSampleData,
    addRow,
    addColumn,
    deleteRow,
    clearTable,
    validateCell,
    applyTotalRows,
    useFirstRowAsHeader,
    useTableAsFile,
    buildBlobFromTable,
    getVariableMappingText,
    getVariableMapping,
  }
}

