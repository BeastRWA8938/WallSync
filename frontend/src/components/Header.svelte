<script>
  let { activeTab } = $props()

  const titles = {
    tasks: 'Tasks',
    calendar: 'Calendar',
    habits: 'Habits',
    agent: 'AI Agent',
  }

  const today = new Intl.DateTimeFormat('en-IN', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
  }).format(new Date())
</script>

<header class="headerContainer">
  <div>
    <p class="eyebrow">WallSync</p>
    <h1>{titles[activeTab] ?? 'Command Center'}</h1>
  </div>
  <time datetime={new Date().toISOString()}>{today}</time>
</header>
