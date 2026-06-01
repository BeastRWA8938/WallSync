<script>
  import Icons from './Icons.svelte'

  let { activeTab, onSelectTab } = $props()

  const tabs = [
    { id: 'tasks', label: 'Tasks' },
    { id: 'calendar', label: 'Calendar' },
    { id: 'habits', label: 'Habits' },
    { id: 'focus', label: 'Focus' },
    { id: 'agent', label: 'AI Agent' },
  ]
</script>

<aside class="sidebarContainer" aria-label="Primary navigation">
  <div class="brandMark">WS</div>

  <nav class="sidebarTabs">
    {#each tabs as tab}
      <button
        type="button"
        class:active={activeTab === tab.id}
        class="sidebarButton"
        aria-label={tab.label}
        aria-current={activeTab === tab.id ? 'page' : undefined}
        title={tab.label}
        onclick={() => onSelectTab(tab.id)}
      >
        <Icons name={tab.id} size={22} />
      </button>
    {/each}
  </nav>
</aside>

