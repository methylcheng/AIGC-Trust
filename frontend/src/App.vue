<template>
    <div id="app">
        <Header />
        <router-view />
    </div>
</template>

<script setup>
import Header from './components/Header.vue'
</script>

<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

#app {
    min-height: 100vh;
}
</style>
