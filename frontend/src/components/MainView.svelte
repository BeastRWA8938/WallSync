<!-- 
 MainView
    - Header
    - Content
-->

<script>
    import Header from './Header.svelte'
    import Content from './Content.svelte'

    let value = $props();
</script>

<div class="mainContainer">
    <Header activeTab={value.activeTab}/>
    <Content activeTab={value.activeTab}/>
</div>
