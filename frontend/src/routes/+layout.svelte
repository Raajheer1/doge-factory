<script lang="ts">
  import Sidebar from '$lib/shell/Sidebar.svelte';
  import Topbar from '$lib/shell/Topbar.svelte';
  import './app.css';

  let { children } = $props();
</script>

<div class="app-shell">
  <Sidebar />
  <main>
    <Topbar />
    <div class="content">
      {@render children()}
      <footer><span>DOGE FACTORY <b> / </b> AI POLICY FACTORY</span><span>Pitch a product. Find the policy in the way. Move it.</span></footer>
    </div>
  </main>
</div>
