<script>
  import AIView from './AIView.svelte'
  import CalendarView from './CalendarView.svelte'
  import HabitsView from './HabitsView.svelte'
  import TaskView from './TaskView.svelte'

  let { activeTab } = $props()
</script>

<div class="contentContainer active-tab-{activeTab}">
  <div class="widgetWrapper tasksWidget">
    <TaskView />
  </div>
  <div class="widgetWrapper calendarWidget">
    <CalendarView />
  </div>
  <div class="widgetWrapper habitsWidget">
    <HabitsView />
  </div>
  <div class="widgetWrapper agentWidget">
    <AIView />
  </div>
</div>

