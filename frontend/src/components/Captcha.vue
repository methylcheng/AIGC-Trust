<template>
    <div class="captcha-container" @click="refreshCaptcha">
        <canvas ref="canvasRef" :width="width" :height="height"></canvas>
    </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
    width: {
        type: Number,
        default: 120
    },
    height: {
        type: Number,
        default: 40
    },
    length: {
        type: Number,
        default: 4
    }
})

const emit = defineEmits(['update:modelValue'])

const canvasRef = ref(null)
const captchaCode = ref('')

// 生成随机颜色
const randomColor = (min, max) => {
    const r = Math.floor(Math.random() * (max - min) + min)
    const g = Math.floor(Math.random() * (max - min) + min)
    const b = Math.floor(Math.random() * (max - min) + min)
    return `rgb(${r},${g},${b})`
}

// 生成验证码
const generateCaptcha = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789' // 去除易混淆字符
    let code = ''
    
    for (let i = 0; i < props.length; i++) {
        code += chars.charAt(Math.floor(Math.random() * chars.length))
    }
    
    captchaCode.value = code
    emit('update:modelValue', code)
    
    drawCaptcha(code)
}

// 绘制验证码
const drawCaptcha = (code) => {
    const canvas = canvasRef.value
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, props.width, props.height)
    
    // 绘制背景
    ctx.fillStyle = randomColor(200, 250)
    ctx.fillRect(0, 0, props.width, props.height)
    
    // 绘制干扰线
    for (let i = 0; i < 5; i++) {
        ctx.strokeStyle = randomColor(100, 200)
        ctx.beginPath()
        ctx.moveTo(Math.random() * props.width, Math.random() * props.height)
        ctx.lineTo(Math.random() * props.width, Math.random() * props.height)
        ctx.stroke()
    }
    
    // 绘制干扰点
    for (let i = 0; i < 30; i++) {
        ctx.fillStyle = randomColor(150, 200)
        ctx.beginPath()
        ctx.arc(Math.random() * props.width, Math.random() * props.height, 1, 0, 2 * Math.PI)
        ctx.fill()
    }
    
    // 绘制文字
    for (let i = 0; i < code.length; i++) {
        const x = (props.width / props.length) * i + 10
        const y = props.height / 2 + 5
        
        ctx.font = `${Math.floor(Math.random() * 10 + 20)}px Arial`
        ctx.fillStyle = randomColor(50, 150)
        ctx.textBaseline = 'middle'
        
        // 随机旋转
        ctx.save()
        ctx.translate(x, y)
        const rotation = (Math.random() - 0.5) * 0.4
        ctx.rotate(rotation)
        ctx.fillText(code[i], 0, 0)
        ctx.restore()
    }
}

// 刷新验证码
const refreshCaptcha = () => {
    generateCaptcha()
}

// 暴露刷新方法
defineExpose({
    refresh: refreshCaptcha
})

// 初始化
onMounted(() => {
    generateCaptcha()
})

// 监听属性变化
watch(() => props.length, () => {
    generateCaptcha()
})
</script>

<style scoped>
.captcha-container {
    cursor: pointer;
    display: inline-block;
    border-radius: 4px;
    overflow: hidden;
    transition: all 0.3s;
}

.captcha-container:hover {
    opacity: 0.8;
    transform: scale(1.02);
}

canvas {
    display: block;
}
</style>
