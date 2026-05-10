<template>
  <div>欢迎，{{ auth.user?.full_name || auth.user?.username }}</div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
</script>
