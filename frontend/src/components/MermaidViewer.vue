<template>
  <div ref="container" class="mermaid-viewer" />
</template>

<script>
import mermaid from 'mermaid/dist/mermaid.esm.mjs'
import svgPanZoom from 'svg-pan-zoom'
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

          // Enable pan & zoom for large diagrams
          this.$nextTick(() => {
            const svgEl = this.$refs.container.querySelector('svg')
            if (svgEl && !svgEl.__panZoomAttached) {
              svgPanZoom(svgEl, {
                controlIconsEnabled: true,
                zoomEnabled: true,
                minZoom: 0.4,
                maxZoom: 5,
                fit: true,
                center: true
              })
              svgEl.__panZoomAttached = true
            }
          })
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
  position: relative;
}

.mermaid-viewer svg {
  width: 100%;
  height: auto;
}
</style> 