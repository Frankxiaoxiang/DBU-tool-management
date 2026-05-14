<template>
  <el-container style="height: 100vh">
    <el-aside width="200px">
      <el-menu default-active="/" router>
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/projects">项目管理</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="layout-header">
        <span class="logo">DBU 模治具管理系统</span>
        <div class="user-area">
          <span class="username">{{ auth.user?.full_name || auth.user?.username }}</span>
          <el-button size="small" @click="handleLogout">退出登录</el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' })
  } catch {
    return
  }

  try {
    await auth.logout()
  } catch {
    ElMessage.error('退出失败，请重试')
  }
}
</script>

<style scoped>
.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e4e7ed;
}
.logo {
  font-weight: 600;
  font-size: 16px;
}
.user-area {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
