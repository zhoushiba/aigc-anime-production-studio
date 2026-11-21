<template>
  <div class="login-page">
    <div class="visual">
      <div class="tag">AIGC × 动漫番剧</div>
      <h1>从一句设定<br />到一集成片</h1>
      <p class="desc">
        剧本构思 → 分镜脚本 → 角色设定卡 → AIGC 生成 → 二次优化 → 合成导出 → 审核交付，
        把动漫制作的前期策划与后期量产放进同一张工作台。
      </p>
      <ul class="features">
        <li><span>01</span> 三幕式 / 起承转合剧本模板与场次拆解</li>
        <li><span>02</span> 8 套镜头语言组合的提示词公式</li>
        <li><span>03</span> 文生图 / 图生视频任务队列与真实状态流转</li>
        <li><span>04</span> 素材评分、问题标注、修正词重绘与并排对比</li>
      </ul>
      <div class="foot muted">离线 Mock 生成器开箱可用 · 可一键切换 ComfyUI / OpenAI 图像服务</div>
    </div>

    <div class="form-wrap">
      <el-card class="card" shadow="never">
        <h2>{{ isRegister ? '注册新成员' : '登录工作台' }}</h2>
        <p class="muted">{{ isRegister ? '选择岗位角色，加入剧组' : '演示账号已内置《星海拾光》完整示例项目' }}</p>

        <el-form :model="form" label-position="top" @submit.prevent="submit">
          <el-form-item label="用户名">
            <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              placeholder="密码"
              size="large"
              :prefix-icon="Lock"
            />
          </el-form-item>
          <template v-if="isRegister">
            <el-form-item label="显示名称">
              <el-input v-model="form.display_name" placeholder="如：林导" size="large" />
            </el-form-item>
            <el-form-item label="岗位角色">
              <el-select v-model="form.role" size="large" style="width: 100%">
                <el-option label="导演" value="director" />
                <el-option label="分镜师" value="storyboard" />
                <el-option label="美术" value="artist" />
                <el-option label="审核" value="reviewer" />
                <el-option label="学员" value="student" />
              </el-select>
            </el-form-item>
          </template>

          <el-button type="primary" size="large" class="submit" :loading="loading" @click="submit">
            {{ isRegister ? '注册并登录' : '登录' }}
          </el-button>
        </el-form>

        <div class="switch">
          <el-button link type="primary" @click="isRegister = !isRegister">
            {{ isRegister ? '已有账号，去登录' : '没有账号？注册一个' }}
          </el-button>
        </div>

        <el-alert type="info" :closable="false" class="hint">
          演示账号：director / anime2025（也可用 storyboard、artist、reviewer、student，密码相同）
        </el-alert>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Lock, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isRegister = ref(false)
const loading = ref(false)
const form = reactive({
  username: 'director',
  password: 'anime2025',
  display_name: '林导',
  role: 'director'
})

// 演示模式：访问 #/login?demo=1 时用默认导演账号自动登录并跳到目标页面，
// 便于部署后一键演示，也用于自动化截图（docs/screenshots）。
onMounted(async () => {
  if (route.query.demo !== '1' || auth.token) {
    return
  }
  loading.value = true
  try {
    await auth.login('director', 'anime2025')
    router.replace((route.query.next as string) || '/dashboard')
  } finally {
    loading.value = false
  }
})

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请填写用户名与密码')
    return
  }
  loading.value = true
  try {
    if (isRegister.value) {
      await auth.register({
        username: form.username,
        password: form.password,
        display_name: form.display_name,
        role: form.role
      })
      ElMessage.success('注册成功，已自动登录')
    } else {
      await auth.login(form.username, form.password)
      ElMessage.success('登录成功')
    }
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch (error) {
    // 错误提示已由 axios 拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
}

.visual {
  padding: 72px 64px;
  background:
    radial-gradient(700px 420px at 15% 10%, rgba(124, 92, 255, 0.35), transparent 60%),
    radial-gradient(600px 420px at 80% 90%, rgba(53, 208, 186, 0.22), transparent 62%),
    #0b0e14;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.tag {
  display: inline-block;
  width: fit-content;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(124, 92, 255, 0.6);
  color: #c9bcff;
  font-size: 12px;
  letter-spacing: 1px;
  margin-bottom: 18px;
}

h1 {
  font-size: 44px;
  line-height: 1.22;
  margin: 0 0 18px;
  letter-spacing: 2px;
}

.desc {
  color: #b6c0d3;
  max-width: 520px;
  line-height: 1.9;
  margin: 0 0 26px;
}

.features {
  list-style: none;
  padding: 0;
  margin: 0 0 30px;
  display: grid;
  gap: 12px;
  max-width: 560px;
}

.features li {
  display: flex;
  gap: 12px;
  align-items: baseline;
  color: #d5dcea;
}

.features span {
  font-family: 'Consolas', monospace;
  color: var(--aigc-accent-2);
  font-size: 12px;
  letter-spacing: 1px;
}

.form-wrap {
  display: grid;
  place-items: center;
  padding: 40px;
  background: #0f131b;
}

.card {
  width: 100%;
  max-width: 380px;
  border: 1px solid var(--aigc-line);
  border-radius: 16px;
  background: #151a24;
  padding: 10px 6px;
}

.card h2 {
  margin: 6px 0 6px;
  font-size: 22px;
}

.card .muted {
  margin: 0 0 18px;
  font-size: 12px;
  line-height: 1.7;
}

.submit {
  width: 100%;
  margin-top: 6px;
}

.switch {
  text-align: center;
  margin: 10px 0 6px;
}

.hint {
  margin-top: 8px;
  font-size: 12px;
}
</style>
