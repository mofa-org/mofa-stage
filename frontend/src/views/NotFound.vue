<template>
  <div class="welcome-page">
    <div class="welcome-container">
      <div class="logo-section">
        <img src="@/assets/mofa-logo.png" alt="MoFA Stage" class="logo" />
        <h1 class="welcome-title">Welcome to MoFA Stage</h1>
        <p class="welcome-subtitle">AI Agent Development Platform</p>
      </div>
      
      <div class="description-section">
        <p class="description">
          Build, test, and deploy intelligent agents with ease. 
          Start your journey into the future of AI development.
        </p>
      </div>
      
      <div class="action-section">
        <el-button type="primary" size="large" @click="goHome" class="get-started-btn">
          Get Started
        </el-button>
      </div>
    </div>
  </div>
</template>

<script>
import { useRouter } from 'vue-router'

export default {
  name: 'NotFound',
  setup() {
    const router = useRouter()
    
    const goHome = () => {
      router.push('/')
    }
    
    return {
      goHome
    }
  }
}
</script>

<style scoped>
.welcome-page {
  min-height: 100vh;
  background: #ffffff;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.welcome-container {
  background: #ffffff;
  padding: 60px 40px;
  max-width: 600px;
  width: 100%;
  text-align: center;
}

.logo-section {
  margin-bottom: 40px;
}

.logo {
  width: 120px;
  height: 120px;
  margin-bottom: 24px;
}

.welcome-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 12px 0;
}

.welcome-subtitle {
  font-size: 1.2rem;
  color: #6c757d;
  margin: 0;
  font-weight: 500;
}

.description-section {
  margin-bottom: 40px;
}

.description {
  font-size: 1.1rem;
  color: #495057;
  line-height: 1.6;
  margin: 0;
  max-width: 480px;
  margin: 0 auto;
}

.action-section {
  margin-top: 40px;
}

.get-started-btn {
  padding: 16px 32px;
  font-size: 1.1rem;
  font-weight: 600;
  border-radius: 0;
  background: #fd533f;
  border: none;
  color: #ffffff;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(253, 83, 63, 0.2);
}

.get-started-btn:hover {
  background: #e8472f;
  box-shadow: 0 4px 12px rgba(253, 83, 63, 0.3);
}

.get-started-btn:active {
  background: #d4402a;
  transform: translateY(1px);
  box-shadow: 0 1px 4px rgba(253, 83, 63, 0.3);
}

@media (max-width: 768px) {
  .welcome-container {
    padding: 40px 24px;
    margin: 20px;
  }
  
  .welcome-title {
    font-size: 2rem;
  }
  
  .logo {
    width: 100px;
    height: 100px;
  }
}
</style>
