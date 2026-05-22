<script>
  import Header from './Header.svelte'
  import Content from './Content.svelte'

  let { activeTab } = $props()
</script>

<main class="mainContainer">
  <Header {activeTab} />
  <Content {activeTab} />
</main>
