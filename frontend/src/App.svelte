<!-- 
 App
    - SideBar
    - MainView
-->

<script>
import SideBar from './components/SideBar.svelte'
import MainView from './components/MainView.svelte'

var activeTab = $state("taskView");

function readIntent (e) {
    activeTab = e.detail;
    console.log("Updated activeTab", activeTab);
}
</script>

<div class="appContainer">
    <MainView activeTab={activeTab} />
    <SideBar activeTab={activeTab} on:intent={readIntent} />
</div>
