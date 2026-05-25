<script>
  import SideBar from './components/SideBar.svelte'
  import MainView from './components/MainView.svelte'

  let activeTab = $state('tasks')
</script>

<div class="appContainer">
  <MainView {activeTab} />
  <SideBar {activeTab} onSelectTab={(tab) => (activeTab = tab)} />
</div>