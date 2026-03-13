<template>
  <div class="tutorial-wrapper">
    <el-card class="tutorial-card" shadow="hover">
      <div class="tutorial-header">
        <h1>如何获取豆瓣 Cookie</h1>
        <p class="subtitle">为了更稳定地抓取图书元数据，建议配置豆瓣 Cookie。</p>
      </div>

      <div class="tutorial-content">
        <el-timeline>
          <el-timeline-item timestamp="第 1 步" placement="top" type="primary">
            <p>打开浏览器，本文以 Chrome (或 Edge 等衍生浏览器) 为例。</p>
          </el-timeline-item>
          
          <el-timeline-item timestamp="第 2 步" placement="top" type="primary">
            <p>访问 <a href="https://douban.com" target="_blank" class="highlight-link">豆瓣网站 (douban.com)</a> 并登录您的账号。</p>
          </el-timeline-item>
          
          <el-timeline-item timestamp="第 3 步" placement="top" type="primary">
            <p>登录成功后，再次访问 <strong>https://douban.com</strong> 确保停留在首页。</p>
          </el-timeline-item>
          
          <el-timeline-item timestamp="第 4 步" placement="top" type="primary">
            <p>打开浏览器的 <strong>开发者工具</strong>：<br>
               按快捷键 <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>I</kbd>，或 <kbd>F12</kbd>，或在网页空白处右键选择“检查(Inspect)”。</p>
          </el-timeline-item>
          
          <el-timeline-item timestamp="第 5 步" placement="top" type="primary">
            <p>在开发者工具面板上方，切换到 <strong>网络 (Network)</strong> 页签。<br>
               <span class="tip-text">提示：如果没有看到记录，请按 F5 刷新一下当前页面。</span></p>
          </el-timeline-item>
          
          <el-timeline-item timestamp="第 6 步" placement="top" type="warning">
            <p>在筛选栏中选择 <strong>全部 (All)</strong> 或者 <strong>文档 (Doc)</strong>。<br>
               在下方的请求列表中，找到最上面名称为 <strong>www.douban.com</strong> 的那一条，并点击它。</p>
          </el-timeline-item>
          
          <el-timeline-item timestamp="第 7 步" placement="top" type="success">
            <p>在右侧弹出的详情面板中，选择 <strong>标头 (Headers)</strong> 栏目。<br>
               往下滚动找到 <strong>请求标头 (Request Headers)</strong> 区域。<br>
               在其中找到名为 <strong>Cookie:</strong> 的字段，右键选中并复制它右侧所有长长的一串值。</p>
            <div class="tutorial-image">
              <img src="@/assets/images/douban-cookie.png" alt="获取豆瓣 Cookie 演示" />
            </div>
          </el-timeline-item>
          
          <el-timeline-item timestamp="最后一步" placement="top" type="success">
            <p>回到 Metomi 的安装向导（或设置页），将刚才复制的那串内容粘贴到 <strong>豆瓣 Cookie</strong> 的输入框中即可。</p>
          </el-timeline-item>
        </el-timeline>
        
        <div class="color-explanation">
          <p><span class="dot warning-dot"></span> <strong>黄色步骤</strong>：需要你仔细辨认并选择正确的网络请求（www.douban.com）。</p>
          <p><span class="dot success-dot"></span> <strong>绿色步骤</strong>：代表获取真正重要数据（Cookie 值）和最终完成配置的关键操作，请对准红框内的区域进行复制。</p>
        </div>
      </div>
      
      <div class="tutorial-footer">
        <el-button type="primary" @click="closeWindow">我已了解，关闭本页</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
const closeWindow = () => {
  window.close();
}
</script>

<style scoped>
.tutorial-wrapper {
  min-height: 100vh;
  padding: 40px 20px;
  display: flex;
  justify-content: center;
  background-color: #f5f7fa;
}

.tutorial-card {
  width: 100%;
  max-width: 800px;
  border-radius: 8px;
  border: none;
}

.tutorial-header {
  text-align: center;
  margin-bottom: 40px;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 20px;
}

.tutorial-header h1 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 26px;
}

.subtitle {
  color: #909399;
  margin: 0;
  font-size: 15px;
}

.tutorial-content {
  padding: 10px 20px;
}

.tutorial-content p {
  margin: 0;
  color: #606266;
  font-size: 15px;
  line-height: 1.6;
}

kbd {
  background-color: #f4f4f4;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-shadow: 0 1px 1px rgba(0,0,0,0.2);
  color: #333;
  display: inline-block;
  font-family: inherit;
  font-size: 0.85em;
  font-weight: 700;
  line-height: 1;
  padding: 2px 6px;
  white-space: nowrap;
  margin: 0 2px;
}

strong {
  color: #303133;
  font-weight: 600;
}

.highlight-link {
  color: #409EFF;
  text-decoration: none;
  font-weight: 500;
}

.highlight-link:hover {
  text-decoration: underline;
}

.tip-text {
  font-size: 13px;
  color: #E6A23C;
  display: inline-block;
  margin-top: 4px;
}

.tutorial-footer {
  margin-top: 40px;
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.tutorial-image {
  margin-top: 15px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.tutorial-image img {
  width: 100%;
  height: auto;
  display: block;
}

.color-explanation {
  margin-top: 30px;
  padding: 15px 20px;
  background-color: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #909399;
}

.color-explanation p {
  margin: 5px 0;
  font-size: 14px;
  line-height: 1.6;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 8px;
  vertical-align: baseline;
}

.warning-dot {
  background-color: #E6A23C;
}

.success-dot {
  background-color: #67C23A;
}
</style>
