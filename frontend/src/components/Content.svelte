<!--
Content
    - TaskView
    - CalendarView
    - AIView
-->

<script>
    let value = $props();
</script>

<div class="contentContainer">
    {#if value.activeTab=="taskView"}
    <p>Task View</p>
    {:else if value.activeTab=="calendarView"}
    <p>Calander View</p>
    {:else if value.activeTab=="aiView"}
    <p>AI View</p>
    {:else}
    <p>Invalid Tab</p>
    {/if}
</div>