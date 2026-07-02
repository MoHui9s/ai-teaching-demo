<script setup>
import { useDarkMode } from './composables/useDarkMode'

const { isDark } = useDarkMode()
</script>

<template>
  <div :class="['app-root', { dark: isDark }]">
    <router-view />
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}

.app-root {
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.app-root.dark {
  background: #1a1a1a;
  color: #e0e0e0;
}
</style>
