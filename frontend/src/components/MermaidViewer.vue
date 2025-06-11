<template>
  <div ref="container" class="mermaid-viewer" />
</template>

<script>
import mermaid from 'mermaid/dist/mermaid.esm.mjs'
export default {
  name: 'MermaidViewer',
  props: {
    code: { type: String, default: '' }
  },
  watch: {
    code: {
      handler() { this.render() },
      immediate: true
    }
  },
  setup() {
    mermaid.initialize({ startOnLoad: false, theme: 'default' })
  },
  methods: {
    render() {
      if (!this.code) return
      try {
        mermaid.render('generated', this.code, (svg) => {
          this.$refs.container.innerHTML = svg
        })
      } catch (err) {
        this.$refs.container.innerHTML = `<pre style="color:red">${err}</pre>`
      }
    }
  }
}
</script>

<style scoped>
.mermaid-viewer {
  overflow: auto;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: flex-start;
}
</style> 