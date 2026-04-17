<template>
  <header class="app-header">
    <div class="header-left">
      <div class="brand" @click="$router.push('/')">CRIMESCOPE</div>
      <span class="version-badge">V1.2</span>
    </div>
    <div class="header-right">
      <div class="step-divider"></div>
      <router-link to="/" class="nav-link">← Cases</router-link>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  height: 60px;
  border-bottom: 1px solid #EAEAEA;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
  background: #FFF;
  z-index: 100;
  position: relative;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800; font-size: 18px;
  letter-spacing: 1px; cursor: pointer;
  color: #000;
}
.version-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; padding: 2px 8px;
  border: 1px solid #E91E63; color: #E91E63;
  border-radius: 4px; text-transform: uppercase;
  letter-spacing: 0.5px;
}
.header-right { display: flex; align-items: center; gap: 16px; }
.step-divider { width: 1px; height: 14px; background: #E0E0E0; }
.nav-link {
  font-size: 13px; font-weight: 500; color: #666;
  padding: 6px 14px; border: 1px solid #E0E0E0;
  border-radius: 6px; transition: all 0.2s;
}
.nav-link:hover { background: #F5F5F5; color: #000; border-color: #CCC; }
</style>
