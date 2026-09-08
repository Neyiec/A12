<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { Microphone } from '@element-plus/icons-vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  label: { type: String, default: '录音输入' },
})

const emit = defineEmits(['recorded', 'error'])

const recording = ref(false)
const seconds = ref(0)
let recorder = null
let stream = null
let chunks = []
let timer = null

const formatSeconds = (value) => {
  const total = Math.max(0, Number(value) || 0)
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

const statusText = computed(() => {
  if (props.busy) return '正在识别…'
  return recording.value ? `录音中 ${formatSeconds(seconds.value)}` : ''
})

const supportedMimeType = () => {
  if (!window.MediaRecorder?.isTypeSupported) return ''
  return [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/mp4',
  ].find((type) => window.MediaRecorder.isTypeSupported(type)) || ''
}

const stopTracks = () => {
  if (stream) stream.getTracks().forEach((track) => track.stop())
  stream = null
}

const clearTimer = () => {
  if (timer) window.clearInterval(timer)
  timer = null
}

const resetRecorder = () => {
  clearTimer()
  stopTracks()
  recorder = null
  chunks = []
  recording.value = false
  seconds.value = 0
}

const finishRecording = () => {
  const mimeType = recorder?.mimeType || 'audio/webm'
  const recordedChunks = chunks
  resetRecorder()
  if (!recordedChunks.length) {
    emit('error', new Error('未录制到有效音频'))
    return
  }
  const blob = new Blob(recordedChunks, { type: mimeType })
  const extension = mimeType.includes('ogg') ? 'ogg' : mimeType.includes('mp4') ? 'mp4' : 'webm'
  emit('recorded', new File([blob], `voice-${Date.now()}.${extension}`, { type: mimeType }))
}

const startRecording = async () => {
  if (props.disabled || props.busy || recording.value) return
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    emit('error', new Error('当前浏览器不支持录音，请使用最新版 Chrome/Edge'))
    return
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mimeType = supportedMimeType()
    recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
    chunks = []
    recorder.ondataavailable = (event) => {
      if (event.data?.size) chunks.push(event.data)
    }
    recorder.onerror = (event) => {
      resetRecorder()
      emit('error', event.error || new Error('录音失败'))
    }
    recorder.onstop = finishRecording
    recorder.start()
    recording.value = true
    seconds.value = 0
    timer = window.setInterval(() => { seconds.value += 1 }, 1000)
  } catch (error) {
    resetRecorder()
    emit('error', error instanceof Error ? error : new Error('无法访问麦克风'))
  }
}

const stopRecording = () => {
  if (!recorder || !recording.value) return
  clearTimer()
  try { recorder.stop() } catch (error) {
    resetRecorder()
    emit('error', error instanceof Error ? error : new Error('停止录音失败'))
  }
}

const toggleRecording = () => {
  if (recording.value) stopRecording()
  else void startRecording()
}

onBeforeUnmount(() => {
  clearTimer()
  if (recorder && recorder.state !== 'inactive') {
    try { recorder.stop() } catch { /* 页面销毁时无需继续提示 */ }
  }
  stopTracks()
})
</script>

<template>
  <span class="voice-recorder-button">
    <el-tooltip :content="recording ? '停止录音并发送' : label">
      <el-button
        text
        circle
        :class="{ 'is-recording': recording }"
        :disabled="disabled || busy"
        :loading="busy"
        :aria-label="recording ? '停止录音' : label"
        @click="toggleRecording"
      >
        <el-icon><Microphone /></el-icon>
      </el-button>
    </el-tooltip>
    <span v-if="statusText" class="voice-recorder-status" role="status">{{ statusText }}</span>
  </span>
</template>

<style scoped>
.voice-recorder-button { display: inline-flex; align-items: center; gap: 6px; }
.voice-recorder-button :deep(.el-button) { color: var(--zh-text-caption); }
.voice-recorder-button :deep(.el-button:hover),
.voice-recorder-button :deep(.el-button:focus-visible),
.voice-recorder-button :deep(.el-button.is-recording) { color: var(--zh-text-theme); background: var(--zh-background-weaken); }
.voice-recorder-button :deep(.el-button.is-recording) { animation: voice-recorder-pulse 1.4s ease-in-out infinite; }
.voice-recorder-status { color: var(--zh-text-theme); font-size: 11px; white-space: nowrap; }
@keyframes voice-recorder-pulse { 50% { box-shadow: 0 0 0 5px var(--zh-line-theme20); } }
</style>
