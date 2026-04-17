<template>
  <div class="platform-feed">
    <div class="feed__tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="feed__tab font-mono"
        :class="{ 'feed__tab--active': activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>
    <div class="feed__list">
      <PostCard
        v-for="post in filteredPosts"
        :key="post.timestamp + post.agent_id"
        :post="post"
      />
      <div v-if="!filteredPosts.length" class="feed__empty font-mono">
        No activity on this platform yet.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import PostCard from './PostCard.vue'

const props = defineProps({
  posts: { type: Array, default: () => [] }
})

const tabs = [
  { id: 'all', label: 'ALL' },
  { id: 'twitter', label: 'PLATFORM A' },
  { id: 'reddit', label: 'PLATFORM B' }
]

const activeTab = ref('all')

const filteredPosts = computed(() => {
  if (activeTab.value === 'all') return props.posts
  return props.posts.filter(p => p.platform === activeTab.value)
})
</script>

<style scoped>
.platform-feed {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.feed__tabs {
  display: flex;
  gap: 2px;
  padding: var(--space-sm);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.feed__tab {
  flex: 1;
  padding: var(--space-sm) var(--space-md);
  font-size: 0.6rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--color-muted);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast) ease;
  text-align: center;
}

.feed__tab:hover {
  color: var(--color-text-secondary);
  background: var(--color-surface-2);
}

.feed__tab--active {
  color: var(--color-primary);
  background: oklch(72% 0.25 145 / 0.08);
}

.feed__list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-sm);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.feed__empty {
  text-align: center;
  color: var(--color-muted);
  padding: var(--space-3xl);
  font-size: 0.75rem;
  letter-spacing: 0.1em;
}
</style>
