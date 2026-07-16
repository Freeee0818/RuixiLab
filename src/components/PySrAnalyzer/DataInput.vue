<template>
  <div class="data-input-section">
    <div class="section-header">
      <div>
        <h4>数据集</h4>
        <p class="section-subtitle">上传或编辑实验数据，并确认变量映射</p>
      </div>
      <div class="source-actions">
        <el-button type="primary" @click="loadDataFile" :disabled="disabled">选择数据文件</el-button>
        <a :href="sampleDataUrl" download="GuideLab示例数据.csv">下载示例数据</a>
      </div>
    </div>
    
    <div class="help-text">文件应包含至少两列数值数据；导入后可在下方校对列名与变量映射。</div>

    <!-- 表格控制按钮 -->
    <div class="table-controls">
      <div class="control-group">
        <el-button size="small" @click="addRow" :disabled="disabled">添加行</el-button>
        <el-button size="small" @click="addColumn" :disabled="disabled">添加列</el-button>
        <el-button size="small" @click="useFirstRowAsHeader" :disabled="!tableData.length || disabled">
          首行作列名
        </el-button>
        <el-button size="small" @click="clearTable" :disabled="disabled">清空</el-button>
        <el-button size="small" @click="loadSampleData" :disabled="disabled">加载示例</el-button>
      </div>

      <div class="control-group row-controls">
        <label>
          <span>行分页</span>
          <el-select v-model="rowGroupIndex" size="small" class="row-select" :disabled="!tableData.length">
            <el-option
              v-for="opt in rowGroupOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </label>
        <label>
          <span>总行数</span>
          <el-input-number v-model="totalRowsDesired" :min="1" :max="10000" size="small" />
        </label>
        <el-button size="small" @click="applyTotalRows" :disabled="disabled">应用</el-button>
      </div>
    </div>
    
    <!-- 可编辑表格 -->
    <div class="editable-table-container">
      <el-table 
        :data="visibleRows" 
        border 
        style="width: 100%"
        :max-height="260"
        class="editable-table"
      >
        <el-table-column 
          v-for="col in tableColumns" 
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          min-width="120"
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
        <el-select v-model="selectedXCols" multiple collapse-tags size="small" class="x-select">
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
        <el-select v-model="selectedYCol" size="small" class="y-select">
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
import sampleDataUrl from '@/assets/sample_data.csv?url'

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
      sampleDataUrl,
    }
  },
}
</script>

<style scoped>
.data-input-section {
  background: var(--gl-surface);
  padding: 0 0 20px;
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 14px;
}

.section-header h4 {
  margin: 0;
  color: var(--gl-text);
  font-size: 15px;
  font-weight: 700;
}

.section-subtitle {
  margin: 5px 0 0;
  font-size: 13px;
  color: var(--gl-text-secondary);
  line-height: 1.5;
}

.source-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 0 0 auto;
}

.source-actions :deep(.el-button) {
  min-height: 36px;
  padding-inline: 16px;
  font-size: 13px;
  font-weight: 600;
}

.source-actions a {
  color: var(--gl-primary);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
}

.source-actions a:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.help-text {
  color: var(--gl-text-secondary);
  font-size: 13px;
  padding: 9px 11px;
  background: var(--gl-surface-subtle);
  border-left: 2px solid var(--gl-primary);
  border-radius: 6px;
}

.table-controls {
  margin: 14px 0 12px;
  display: flex;
  justify-content: space-between;
  gap: 12px 18px;
  align-items: center;
  flex-wrap: wrap;
}

.control-group,
.row-controls,
.row-controls label {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.row-controls label > span {
  color: var(--gl-text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.row-select {
  width: 138px;
}

.editable-table-container {
  margin-bottom: 14px;
  border: 1px solid var(--gl-border);
  border-radius: 8px;
  overflow: hidden;
}

.editable-table {
  font-size: 13px;
}

.editable-table :deep(.el-table__cell) {
  padding: 5px;
}

.editable-table :deep(.el-input__inner) {
  border: none;
  background: transparent;
  padding: 2px 4px;
  font-size: 13px;
}

.editable-table :deep(.el-input__inner:focus) {
  background: var(--gl-primary-soft);
}

.col-pickers {
  display: flex;
  gap: 14px;
  align-items: center;
  flex-wrap: wrap;
}

.col-pickers label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--gl-text-secondary);
}

.x-select {
  width: 220px;
}

.y-select {
  width: 120px;
}

@media (max-width: 720px) {
  .data-input-section {
    padding-bottom: 16px;
  }

  .section-header {
    flex-direction: column;
    gap: 14px;
  }

  .source-actions {
    width: 100%;
  }

  .source-actions :deep(.el-button) {
    flex: 1;
  }

  .table-controls,
  .control-group,
  .row-controls {
    width: 100%;
  }

  .row-controls label:first-child {
    flex: 1 1 160px;
  }

  .row-select {
    flex: 1;
    width: auto;
  }

  .col-pickers,
  .col-pickers label {
    width: 100%;
    align-items: stretch;
  }

  .col-pickers label {
    flex-direction: column;
  }

  .x-select,
  .y-select,
  .col-pickers :deep(.el-button) {
    width: 100%;
  }
}
</style>
