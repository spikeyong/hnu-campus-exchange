<script setup>
defineProps({ name: { type: String, default: 'arrow' } })
const paths = {
  home: 'm3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z',
  grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  box: 'm12 3 9 5-9 5-9-5 9-5Z M3 8v9l9 5 9-5V8 M12 13v9 M7.5 5.5l9 5',
  skill: 'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z',
  exchange: 'M4 7h16m-4-4 4 4-4 4 M20 17H4m4-4-4 4 4 4',
  file: 'M14 3H5v18h14V8l-5-5Z M14 3v5h5 M8 12h8 M8 16h6',
  heart: 'M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z',
  shield: 'M12 3 3 7v6c0 5 9 9 9 9s9-4 9-9V7l-9-4Z m-4 9 3 3 5-6',
  arrow: 'M4 12h16m-6-6 6 6-6 6',
  plus: 'M12 5v14 M5 12h14',
  user: 'M20 21v-2a7 7 0 0 0-14 0v2 M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  menu: 'M4 6h16 M4 12h16 M4 18h16',
  close: 'm6 6 12 12 M6 18 18 6',
  logout: 'M9 3H4v18h5 M10 12h11m-4-4 4 4-4 4',
  search: 'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
  chevron: 'm8 10 4 4 4-4',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4',
  eye: 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z',
  filter: 'M4 5h16l-6 8v5l-4 2v-7L4 5Z',
  message: 'M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v8Z',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M12 7v5l3 2',
  calendar: 'M7 2v3 M17 2v3 M3 9h18 M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2Z',
  pin: 'M12 21s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12Z M12 11a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z',
  spark: 'm12 3 2 6 6 2-6 2-2 6-2-6-6-2 6-2 2-6Z',
}
</script>

<template>
  <svg class="app-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path :d="paths[name] || paths.arrow" /></svg>
</template>
