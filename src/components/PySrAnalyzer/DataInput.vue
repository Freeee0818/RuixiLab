<template>
  <div class="data-input-section">
    <div class="section-header">
      <h4>数据文件</h4>
      <p class="section-subtitle">上传或编辑数据文件，支持 CSV、TXT 格式</p>
    </div>
    
    <div class="help-text">文件应包含至少两列数据：x和y</div>
    
    <div class="sample-data">
      <a href="/单摆实验数据.txt" download="单摆实验数据.txt">下载示例数据</a>
    </div>

    <!-- 表格控制按钮 -->
    <div class="table-controls">
      <el-button size="small" @click="loadDataFile" :disabled="disabled">加载数据文件</el-button>
      <el-button size="small" @click="addRow" :disabled="disabled">添加行</el-button>
      <el-button size="small" @click="addColumn" :disabled="disabled">添加列</el-button>
      <el-button size="small" @click="clearTable" :disabled="disabled">清空</el-button>
      <el-button size="small" @click="loadSampleData" :disabled="disabled">加载示例</el-button>
      <el-button size="small" @click="useFirstRowAsHeader" :disabled="!tableData.length || disabled">
        第一行作列名
      </el-button>
      
      <span style="margin-left: 8px;">行分页：</span>
      <el-select v-model="rowGroupIndex" size="small" style="width: 160px" :disabled="!tableData.length">
        <el-option 
          v-for="opt in rowGroupOptions" 
          :key="opt.value" 
          :label="opt.label" 
          :value="opt.value"
        />
      </el-select>
      
      <span style="margin-left: 8px;">总行数：</span>
      <el-input-number v-model="totalRowsDesired" :min="1" :max="10000" size="small" />
      <el-button size="small" @click="applyTotalRows" :disabled="disabled">设置行数</el-button>
    </div>
    
    <!-- 可编辑表格 -->
    <div class="editable-table-container">
      <el-table 
        :data="visibleRows" 
        border 
        style="width: 100%"
        :max-height="300"
        class="editable-table"
      >
        <el-table-column 
          v-for="col in tableColumns" 
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          width="120"
        >
          <template #default="scope">
            <el-input
              v-model="scope.row[col.prop]"
              size="small"
              @blur="validateCell(scope.row, col.prop)"
            />
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="scope">
            <el-button 
              type="danger" 
              size="small" 
              @click="deleteRow(scope.$index)"
              :disabled="disabled"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 列选择器 -->
    <div class="col-pickers">
      <label>
        X 列（可多选）：
        <el-select v-model="selectedXCols" multiple collapse-tags size="small" style="min-width: 220px">
          <el-option 
            v-for="col in availableTableCols" 
            :key="col.value" 
            :label="col.label" 
            :value="col.value"
          />
        </el-select>
      </label>
      
      <label>
        Y 列：
        <el-select v-model="selectedYCol" size="small" style="width: 120px">
          <el-option 
            v-for="col in availableTableCols" 
            :key="col.value" 
            :label="col.label" 
            :value="col.value"
          />
        </el-select>
      </label>
      
      <el-button 
        type="primary" 
        size="small" 
        @click="handleUseTable" 
        :disabled="!canUseTable || disabled"
      >
        使用为当前数据
      </el-button>
    </div>
  </div>
</template>

<script>
import { useDataTable } from './composables/useDataTable'

export default {
  name: 'DataInput',
  
  props: {
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  
  emits: ['file-loaded', 'table-used'],
  
  setup(props, { emit }) {
    const {
      tableData,
      tableColumns,
      selectedXCols,
      selectedYCol,
      rowGroupIndex,
      totalRowsDesired,
      rowGroupOptions,
      visibleRows,
      availableTableCols,
      canUseTable,
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
      getVariableMapping,
      getVariableMappingText,
    } = useDataTable()
    
    const handleUseTable = () => {
      const file = useTableAsFile()
      if (file) {
        emit('table-used', file)
      }
    }
    
    return {
      tableData,
      tableColumns,
      selectedXCols,
      selectedYCol,
      rowGroupIndex,
      totalRowsDesired,
      rowGroupOptions,
      visibleRows,
      availableTableCols,
      canUseTable,
      loadDataFile,
      loadSampleData,
      addRow,
      addColumn,
      deleteRow,
      clearTable,
      validateCell,
      applyTotalRows,
      useFirstRowAsHeader,
      handleUseTable,
      getVariableMapping,
      getVariableMappingText,
    }
  },
}
</script>

<style scoped>
.data-input-section {
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #fafbff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 24px 26px 28px;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  overflow: hidden;
}

.data-input-section::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

.section-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid rgba(63, 122, 224, 0.1);
}

.section-header h4 {
  margin: 0;
  color: #1f2d3d;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.section-subtitle {
  margin: 0;
  font-size: 13px;
  color: #7b8a9a;
  line-height: 1.5;
}

.help-text {
  color: #7b8a9a;
  font-size: 13px;
  margin-top: 12px;
  padding: 10px 14px;
  background: rgba(63, 122, 224, 0.06);
  border-left: 3px solid rgba(63, 122, 224, 0.4);
  border-radius: 6px;
}

.sample-data {
  margin-top: 12px;
}

.sample-data a {
  color: #3f7ae0;
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 6px;
  background: rgba(63, 122, 224, 0.08);
  transition: all 0.3s;
  display: inline-block;
}

.sample-data a:hover {
  background: rgba(63, 122, 224, 0.15);
  color: #2d5fc7;
  transform: translateY(-1px);
}

.table-controls {
  margin: 16px 0 12px 0;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.editable-table-container {
  margin-bottom: 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
}

.editable-table {
  font-size: 13px;
}

.editable-table :deep(.el-table__cell) {
  padding: 4px;
}

.editable-table :deep(.el-input__inner) {
  border: none;
  background: transparent;
  padding: 2px 4px;
  font-size: 13px;
}

.editable-table :deep(.el-input__inner:focus) {
  background: #f0f9ff;
  border: 1px solid #409eff;
}

.col-pickers {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.col-pickers label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #606266;
}
</style>

