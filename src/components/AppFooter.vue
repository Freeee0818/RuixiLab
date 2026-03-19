<template>
  <footer class="app-footer">
    <div class="footer-container">
      <span class="platform-name">睿析实验数据分析平台</span>
      <span class="footer-divider">|</span>
      <a
        href="https://beian.miit.gov.cn/"
        target="_blank"
        rel="noopener noreferrer"
        class="footer-link"
      >
        皖ICP备2026003182号
      </a>
    </div>
  </footer>
</template>

<script>
export default {
  name: "AppFooter",
};
</script>

<style scoped>
.app-footer {
  margin-top: auto;
  padding: 16px 24px;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
  text-align: center;
}

.footer-container {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0 12px;
  font-size: 12px;
  color: #6b7280;
}

.platform-name {
  font-size: 13px;
  font-weight: 500;
  color: #4b5563;
}

.footer-divider {
  color: #d1d5db;
}

.footer-link {
  color: #6b7280;
  text-decoration: none;
  transition: color 0.2s;
}

.footer-link:hover {
  color: #1e40af;
}
</style>
