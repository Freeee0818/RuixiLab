<template>
  <div class="data-collection-view">
    <div class="content-container">
      <h1 class="page-title">数据采集工具</h1>
      <p class="page-description">
        选择合适的数据采集工具来收集您的物理实验数据
      </p>

      <div class="tools-grid">
        <div class="tool-card" @click="showModal('tracker')">
          <div class="tool-content">
            <img
              src="@/assets/tools/tracker_logo.png"
              alt="Tracker"
              class="tool-logo"
            />
            <h3 class="tool-title">Tracker</h3>
          </div>
        </div>

        <div class="tool-card" @click="showModal('labview')">
          <div class="tool-content">
            <img
              src="@/assets/tools/labview_logo.png"
              alt="LabVIEW"
              class="tool-logo"
            />
            <h3 class="tool-title">LabVIEW</h3>
          </div>
        </div>

        <div class="tool-card" @click="showModal('phyphox')">
          <div class="tool-content">
            <img
              src="@/assets/tools/phyphox_logo.png"
              alt="PhyPhox"
              class="tool-logo"
            />
            <h3 class="tool-title">手机物理工坊</h3>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showDownloadModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ currentTool.title }}</h3>
          <div class="header-actions">
            <button
              v-if="currentTool.hasGuide"
              class="helper-button"
              @click="showGuide"
            >
              应用使用小助手
            </button>
            <button class="close-button" @click="closeModal">×</button>
          </div>
        </div>
        <div class="modal-body">
          <div
            v-for="(link, index) in currentTool.links"
            :key="index"
            class="download-option"
          >
            <a :href="link.url" target="_blank" class="download-link">{{
              link.name
            }}</a>
          </div>

          <div class="official-site">
            <a :href="currentTool.website" target="_blank" class="website-link"
              >访问官网</a
            >
          </div>
        </div>
      </div>
    </div>

    <div v-if="showGuideModal" class="modal-overlay" @click="closeGuide">
      <div class="modal-content guide-modal" @click.stop>
        <div class="modal-header">
          <h3>应用使用小助手</h3>
          <button class="close-button" @click="closeGuide">×</button>
        </div>
        <div class="modal-body guide-content">
          <div v-html="currentGuideContent"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from "vue";

export default {
  name: "DataCollectionView",

  setup() {
    const showDownloadModal = ref(false);
    const showGuideModal = ref(false);
    const currentTool = ref({});
    const currentGuideContent = ref("");

    // 定义工具数据
    const tools = {
      tracker: {
        title: "Tracker 视频分析",
        website: "https://opensourcephysics.github.io/tracker-website/",
        hasGuide: true,
        guide: `
          <h3>一、标准操作流程</h3>
          <h4>1. 设置坐标轴</h4>
          <p>点击“坐标轴”相关菜单，选中坐标轴。</p>
          <p>点击“原点”以调整坐标原点位置。</p>
          <p>根据实验画面需要旋转坐标轴（例如让 x 水平、y 竖直）。</p>
          
          <h4>2. 创建质点并框选摆球</h4>
          <p>在菜单中选择“创建质点”。</p>
          <p>同时按下 Ctrl + Shift，鼠标会变成圆圈。</p>
          <p>用圆圈选中要识别的物体（摆球），点击后可调整选取区域大小。</p>
          <p><strong>注意</strong>：选取区域应包含摆球边界，避免追踪漂移或丢点。</p>
          <p>点击“搜索”按键，查看结果图（确认是否正确识别到摆球）。</p>
          
          <h4>3. 开始追踪与查看图表物理量</h4>
          <p>点击“搜索”按键，开始追踪摆球位置。</p>
          <p>在图表区选择需要测量/显示的物理量（如位置随时间变化等）。</p>
          
          <h4>4. 导出数据</h4>
          <p>依次点击：文件 / 导出 / 数据文件。</p>
          <p>在弹出的表格中选择要导出的数据列。</p>
          <p>另存为文本数据（.txt）文件，供后续平台/算法分析使用。</p>
          
          <h3>二、常见问题排查</h3>
          <p><strong>追踪不稳定/跳点</strong>：优先检查“选取区域”是否过小或未覆盖摆球边界；必要时重新框选后再搜索。</p>
          <p><strong>数据方向看起来不对</strong>：重新调整坐标轴方向与原点位置。</p>
          <p><strong>导出数据缺列</strong>：导出时确认表格中已勾选需要的数据列。</p>
        `,
        links: [
          {
            name: "Windows x64 安装包（Tracker 6.3.3）",
            url: "https://www.compadre.org/osp/images/tracker/Tracker-6.3.3-windows-x64-installer.exe",
          },
          {
            name: "macOS 安装包（Tracker 6.3.3，较新系统）",
            url: "https://www.compadre.org/osp/images/tracker/Tracker-6.3.3-osx-installer.dmg",
          },
          {
            name: "Linux x64 安装包（Tracker 6.2.0）",
            url: "https://www.compadre.org/osp/images/tracker/Tracker-6.2.0-linux-x64-installer.run",
          },
          {
            name: "Linux 升级包（Tracker 6.3.3 Upgrade）",
            url: "https://www.compadre.org/osp/images/tracker/TrackerUpgrade-6.3.3-linux-x64-installer.run",
          },
        ],
      },
      labview: {
        title: "LabVIEW 数据采集",
        website:
          "https://www.ni.com/en/support/downloads/software-products/download.labview.html",
        hasGuide: true,
        guide: `
          <h3>一、通用操作模板</h3>
          <h4>1. 硬件连接</h4>
          <p>按实验要求连接传感器与采集设备，确认供电与接口无误。</p>
          
          <h4>2. 打开采集程序</h4>
          <p>启动 LabVIEW，并打开实验室提供的采集工程/VI（具体文件名以现场为准）。</p>
          
          <h4>3. 运行采集</h4>
          <p>点击运行后观察波形/数值是否正常变化，必要时按实验要求调整采样相关参数（若 VI 提供该入口）。</p>
          
          <h4>4. 停止与保存</h4>
          <p>停止采集后，保存数据文件；同时对关键波形/界面进行截图留存。</p>
        `,
        links: [
          {
            name: "LabVIEW 官方下载页",
            url: "https://www.ni.com/en/support/downloads/software-products/download.labview.html",
          },
          {
            name: "LabVIEW Community Edition（免费非商业使用）",
            url: "https://www.ni.com/en/shop/labview/select-edition/labview-community-edition.html",
          },
        ],
      },
      phyphox: {
        title: "手机物理工坊 (PhyPhox)",
        website: "https://phyphox.org/download/",
        hasGuide: false,
        links: [
          {
            name: "Android（Google Play）",
            url: "https://play.google.com/store/apps/details?id=de.rwth_aachen.phyphox",
          },
          {
            name: "iOS（App Store，中国区示例）",
            url: "https://apps.apple.com/cn/app/phyphox/id1127319693",
          },
        ],
      },
    };

    const showModal = (toolKey) => {
      currentTool.value = tools[toolKey];
      showDownloadModal.value = true;
    };

    const closeModal = () => {
      showDownloadModal.value = false;
    };

    const showGuide = () => {
      currentGuideContent.value = currentTool.value.guide;
      showGuideModal.value = true;
    };

    const closeGuide = () => {
      showGuideModal.value = false;
    };

    return {
      showDownloadModal,
      showGuideModal,
      currentTool,
      currentGuideContent,
      showModal,
      closeModal,
      showGuide,
      closeGuide,
    };
  },
};
</script>

<style scoped>
.data-collection-view {
  min-height: 100vh;
  padding: 120px 20px 40px;
  background: #f8fafc;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue",
    Arial, sans-serif;
  color: #1f2937;
}

.content-container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 2.5rem;
  font-weight: 700;
  text-align: center;
  margin-bottom: 1rem;
  color: #1e40af;
}

.page-description {
  font-size: 1.2rem;
  text-align: center;
  color: #6b7280;
  margin-bottom: 3rem;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  margin-top: 2rem;
}

.tool-card {
  background: white;
  border-radius: 12px;
  padding: 3rem 2rem;
  text-align: center;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  cursor: pointer;
  border: 1px solid #e5e7eb;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tool-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  border-color: #3b82f6;
}

.tool-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  width: 100%;
}

.tool-logo {
  width: 80px;
  height: 80px;
  object-fit: contain;
}

.tool-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.5rem;
  color: #1f2937;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.helper-button {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.helper-button:hover {
  background: #2563eb;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
  flex-shrink: 0;
}

.close-button:hover {
  color: #1f2937;
  background: #f3f4f6;
}

.modal-body {
  padding: 1.5rem;
}

.download-option {
  margin-bottom: 1rem;
}

.download-link {
  display: block;
  padding: 0.75rem 1rem;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  color: #2563eb;
  text-decoration: none;
  transition: all 0.2s;
}

.download-link:hover {
  background: #dbeafe;
  border-color: #93c5fd;
}

.official-site {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
  text-align: center;
}

.website-link {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: #1e40af;
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 500;
  transition: background 0.2s;
}

.website-link:hover {
  background: #1d4ed8;
}

.guide-modal {
  max-width: 800px;
}

.guide-content {
  max-height: 60vh;
  overflow-y: auto;
  text-align: left;
}

.guide-content h3 {
  color: #1e40af;
  font-size: 1.25rem;
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  text-align: left;
}

.guide-content h3:first-child {
  margin-top: 0;
}

.guide-content h4 {
  color: #374151;
  font-size: 1.1rem;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  text-align: left;
}

.guide-content p {
  color: #4b5563;
  line-height: 1.6;
  margin-bottom: 0.5rem;
  text-align: left;
}

.guide-content strong {
  color: #1f2937;
  font-weight: 600;
}

@media (max-width: 768px) {
  .data-collection-view {
    padding: 100px 15px 30px;
  }

  .page-title {
    font-size: 2rem;
  }

  .tools-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .modal-content {
    margin: 10px;
    max-height: 90vh;
  }
}

@media (min-width: 769px) and (max-width: 1024px) {
  .tools-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 1.5rem;
  }

  .tool-card {
    padding: 2rem 1rem;
  }

  .tool-title {
    font-size: 1.4rem;
  }
}
</style>

