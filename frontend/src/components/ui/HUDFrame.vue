<template>
  <div class="hud-frame">
    <span class="hud-corner hud-tl" aria-hidden="true"></span>
    <span class="hud-corner hud-tr" aria-hidden="true"></span>
    <span class="hud-corner hud-bl" aria-hidden="true"></span>
    <span class="hud-corner hud-br" aria-hidden="true"></span>
    <div class="hud-frame__content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.hud-frame {
  position: relative;
  padding: var(--space-lg);
}

.hud-corner {
  position: absolute;
  width: 16px;
  height: 16px;
  border-color: var(--color-primary);
  border-style: solid;
  opacity: 0.5;
}

.hud-tl { top: 0; left: 0; border-width: 1px 0 0 1px; }
.hud-tr { top: 0; right: 0; border-width: 1px 1px 0 0; }
.hud-bl { bottom: 0; left: 0; border-width: 0 0 1px 1px; }
.hud-br { bottom: 0; right: 0; border-width: 0 1px 1px 0; }

.hud-frame__content {
  position: relative;
}
</style>
