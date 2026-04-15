<!-- 
 SideBar
-->
<script>
import { createEventDispatcher } from "svelte";

const dispatch = createEventDispatcher();

    let value = $props();
    let icon_list = [
        {'id':'taskView', 'label':'Task'},
        {'id':'calendarView', 'label':'Calendar'},
        {'id':'aiView', 'label':'AI'},
    ]

    function intent (tabName) {
        console.log(tabName);
        dispatch('intent', tabName);
    }
</script>

<div class="sidebarContainer">
    <div class="sidebarTabs">
        {#each icon_list as icon}
        <button onclick={() => intent(icon.id)} class="sidebarButtons {value.activeTab === icon.id ? 'active' : ''}">
            <div>{icon.label}</div>
        </button>
        {/each}
    </div>
</div>