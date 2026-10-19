<script setup>
import AppIcon from './AppIcon.vue'
defineProps({ isAdmin: Boolean })
defineEmits(['browse', 'publish'])
</script>

<template>
  <section class="exchange-home" aria-labelledby="exchange-title">
    <div class="campus-art" aria-hidden="true">
      <img class="campus-layer campus-layer--background" src="/exchange/campus-background.webp" alt="" width="1920" height="1080" fetchpriority="high" />
      <img class="campus-layer campus-layer--lake" src="/exchange/campus-lake.webp" alt="" width="1920" height="1080" />
      <img class="campus-layer campus-layer--building" src="/exchange/campus-building.webp" alt="" width="1920" height="1080" />
      <img class="campus-layer campus-layer--trees" src="/exchange/campus-trees.webp" alt="" width="1920" height="1080" />
    </div>

    <div class="exchange-title">
      <h1 id="exchange-title">EXCHANGE</h1>
      <p>在海大，让分享成为日常。</p>
    </div>

    <div class="exchange-welcome">
      <p>把闲置交给需要的人，把擅长分享给身边的同学。<br class="desktop-break" />从一本教材、一项技能开始，发现校园里的更多可能。</p>
      <div class="exchange-actions">
        <button class="home-primary" @click="$emit('browse', 'all')">进入互助广场 <AppIcon name="arrow" /></button>
        <button v-if="!isAdmin" class="home-secondary" @click="$emit('publish')">我也想分享 <AppIcon name="plus" /></button>
      </div>
      <div class="home-shortcuts" aria-label="按类型浏览">
        <button @click="$emit('browse', 'resource')">找一件需要的物品</button>
        <span aria-hidden="true">/</span>
        <button @click="$emit('browse', 'skill')">发现同学的拿手好戏</button>
      </div>
    </div>

    <footer class="exchange-footer">
      <span>海南大学 · 校园资源与技能互助</span>
      <span>彼此确认，安心交付。付款由双方线下完成。</span>
    </footer>
  </section>
</template>
