<template>
  <div class="post-card" :class="`post-card--${post.stance || 'neutral'}`">
    <div class="post-card__avatar" :style="{ borderColor: factionColor }">
      {{ initials }}
    </div>
    <div class="post-card__body">
      <div class="post-card__header">
        <span class="post-card__name font-display">{{ post.agent_name || 'Unknown' }}</span>
        <span class="post-card__platform font-mono">{{ platformLabel }}</span>
        <span class="post-card__time font-mono">{{ timeAgo }}</span>
      </div>
      <p class="post-card__content">{{ post.content }}</p>
      <div class="post-card__footer">
        <span class="post-card__action-type font-mono">
          <span class="post-card__action-icon">{{ actionIcon }}</span>
          {{ post.action_type || 'post' }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  post: { type: Object, required: true }
})

const initials = computed(() =>
  (props.post.agent_name || '?').split(' ').map(w => w[0]).join('')
)

const factionColor = computed(() => {
  const s = props.post.stance
  if (s === 'pro' || (typeof s === 'number' && s > 0.3)) return 'var(--color-primary)'
  if (s === 'hostile' || (typeof s === 'number' && s < -0.3)) return 'var(--color-danger)'
  return 'var(--color-muted)'
})

const platformLabel = computed(() =>
  props.post.platform === 'twitter' ? 'PLATFORM·A' : 'PLATFORM·B'
)

const actionIcon = computed(() => {
  switch (props.post.action_type) {
    case 'retweet': return '↻'
    case 'reply': return '↩'
    case 'upvote': return '▲'
    default: return '◈'
  }
})

const timeAgo = computed(() => {
  if (!props.post.timestamp) return ''
  const diff = Date.now() - props.post.timestamp
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  return `${Math.floor(mins / 60)}h ago`
})
</script>

<style scoped>
.post-card {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  transition: all var(--duration-fast) ease;
  animation: post-slide-in 0.4s var(--ease-out-expo) both;
}

.post-card:hover {
  background: var(--color-surface-2);
}

@keyframes post-slide-in {
  from { opacity: 0; transform: translateY(-8px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.post-card__avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 700;
  background: oklch(8% 0.01 260);
  flex-shrink: 0;
}

.post-card__body {
  flex: 1;
  min-width: 0;
}

.post-card__header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.post-card__name {
  font-weight: 600;
  font-size: 0.85rem;
}

.post-card__platform {
  font-size: 0.55rem;
  color: var(--color-accent);
  letter-spacing: 0.1em;
  background: oklch(68% 0.22 290 / 0.1);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
}

.post-card__time {
  font-size: 0.6rem;
  color: var(--color-muted);
  margin-left: auto;
}

.post-card__content {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-sm);
}

.post-card__footer {
  display: flex;
  align-items: center;
}

.post-card__action-type {
  font-size: 0.6rem;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  display: flex;
  align-items: center;
  gap: 4px;
}

.post-card__action-icon {
  font-size: 0.8rem;
}
</style>
