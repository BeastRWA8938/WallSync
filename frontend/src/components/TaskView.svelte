<script>
  import { onMount } from 'svelte'
  import Icons from './Icons.svelte'

  const API_BASE = import.meta.env.DEV ? 'http://127.0.0.1:5000' : ''

  let tasks = $state([])
  let newTaskTitle = $state('')
  let isLoading = $state(true)
  let isSaving = $state(false)
  let needsAuth = $state(false)
  let error = $state('')
  let completingTasks = $state(new Set())

  async function request(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
      ...options,
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      throw new Error(payload.error ?? 'Task operation failed')
    }

    return response.json()
  }

  async function loadTasks() {
    isLoading = true
    error = ''
    try {
      const payload = await request('/api/tasks')
      if (payload.needsAuth) {
        needsAuth = true
        tasks = []
      } else {
        needsAuth = false
        tasks = payload.tasks ?? []
      }
    } catch (err) {
      error = err.message
    } finally {
      isLoading = false
    }
  }

  async function addTask() {
    const title = newTaskTitle.trim()
    if (!title || isSaving) return

    isSaving = true
    error = ''
    try {
      const payload = await request('/api/tasks', {
        method: 'POST',
        body: JSON.stringify({ title }),
      })
      if (payload.task) {
        tasks = [...tasks, payload.task]
      }
      newTaskTitle = ''
    } catch (err) {
      error = err.message
    } finally {
      isSaving = false
    }
  }

  async function completeTask(listId, taskId) {
    if (completingTasks.has(taskId)) return

    completingTasks.add(taskId)
    completingTasks = new Set(completingTasks)

    try {
      await request(`/api/tasks/${listId}/${taskId}/complete`, { method: 'POST' })
      
      // Delay removal for satisfying completed slide-out/fade animation
      setTimeout(() => {
        tasks = tasks.filter((t) => t.id !== taskId)
        completingTasks.delete(taskId)
        completingTasks = new Set(completingTasks)
      }, 350)
    } catch (err) {
      completingTasks.delete(taskId)
      completingTasks = new Set(completingTasks)
      error = err.message
    }
  }

  onMount(loadTasks)
</script>

<section class="panel scrollPanel tasksPanel">
  <div class="sectionHeader">
    <h2>✓ Today's Tasks</h2>
    <div class="headerActions">
      <span class="statusPill">{needsAuth ? 'Auth Required' : 'Microsoft To Do'}</span>
      <button class="refreshButton" aria-label="Refresh tasks" onclick={loadTasks} disabled={isLoading}>
        <Icons name="agent" size={14} class={isLoading ? 'spinning' : ''} />
      </button>
    </div>
  </div>

  {#if error}
    <p class="errorText">{error}</p>
  {/if}

  {#if needsAuth}
    <div class="authRequiredCard">
      <div class="authIconWrapper">
        <Icons name="lock" size={32} />
      </div>
      <h3>Microsoft Graph Authentication Required</h3>
      <p>WallSync synchronizes with your personal Microsoft To Do lists. You need to perform a one-time secure browser authentication to grant the required permissions.</p>
      <div class="authInstructions">
        <strong>Setup Guide:</strong>
        <ol>
          <li>Open your terminal in the workspace root.</li>
          <li>Run the login script:
            <code>cd backend; ..\venv\Scripts\python.exe auth_setup.py</code>
          </li>
          <li>Log in via the secure browser window that opens.</li>
          <li>Restart your Flask server and refresh this page.</li>
        </ol>
      </div>
      <button class="retryButton" type="button" onclick={loadTasks}>
        <Icons name="agent" size={16} /> Check Authentication Status
      </button>
    </div>
  {:else}
    <form class="inlineForm" onsubmit={(event) => { event.preventDefault(); addTask() }}>
      <input bind:value={newTaskTitle} type="text" placeholder="Add a new Microsoft To Do task..." aria-label="New task title" />
      <button type="submit" disabled={isSaving || !newTaskTitle.trim()}>
        {isSaving ? 'Adding...' : 'Add'}
      </button>
    </form>

    {#if isLoading}
      <div class="emptyState">Loading your tasks from Microsoft Graph...</div>
    {:else if tasks.length === 0}
      <div class="emptyState">All tasks complete! Outstanding work.</div>
    {:else}
      <div class="taskList">
        {#each tasks as task (task.id)}
          <article class="taskRow" class:taskCompleting={completingTasks.has(task.id)}>
            <button
              type="button"
              class="taskCheckbox"
              class:checked={completingTasks.has(task.id)}
              aria-label="Complete task"
              onclick={() => completeTask(task.list_id, task.id)}
            >
              {#if completingTasks.has(task.id)}
                <Icons name="check" size={12} />
              {/if}
            </button>
            <div class="taskContent">
              <span class="taskTitle">{task.title}</span>
              {#if task.dueDateTime}
                <span class="taskDueDate">
                  Due: {new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short' }).format(new Date(task.dueDateTime.dateTime))}
                </span>
              {/if}
            </div>
          </article>
        {/each}
      </div>
    {/if}
  {/if}
</section>

<style>
  .tasksPanel {
    display: flex;
    flex-direction: column;
  }

  .authRequiredCard {
    border: 1px solid #242c38;
    border-radius: 8px;
    background: #101722;
    padding: 24px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    margin: auto 0;
  }

  .authIconWrapper {
    color: #4a8dd8;
    background: rgba(74, 141, 216, 0.1);
    width: 64px;
    height: 64px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    border: 1px solid rgba(74, 141, 216, 0.2);
    margin-bottom: 8px;
  }

  .authRequiredCard h3 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 600;
  }

  .authRequiredCard p {
    color: #aeb9c8;
    max-width: 480px;
    line-height: 1.5;
    margin: 0;
    font-size: 0.9rem;
  }

  .authInstructions {
    text-align: left;
    background: #080b10;
    border: 1px solid #1c232e;
    border-radius: 6px;
    padding: 16px;
    font-size: 0.85rem;
    width: 100%;
    max-width: 480px;
  }

  .authInstructions strong {
    display: block;
    margin-bottom: 8px;
  }

  .authInstructions ol {
    margin: 0;
    padding-left: 20px;
    display: grid;
    gap: 6px;
    color: #8b98aa;
  }

  .authInstructions code {
    background: #182232;
    padding: 2px 6px;
    border-radius: 4px;
    color: #8fb9ff;
    font-family: Consolas, monospace;
    display: block;
    margin-top: 4px;
    overflow-x: auto;
  }

  .retryButton {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: 1px solid #4a8dd8;
    border-radius: 8px;
    background: #1d4f86;
    color: white;
    padding: 10px 16px;
    margin-top: 8px;
    font-size: 0.88rem;
    font-weight: 500;
  }

  .retryButton:hover {
    background: #2561a3;
  }

  .taskList {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
  }

  @media (min-width: 1024px) {
    .taskList {
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 12px;
    }
  }

  .taskRow {
    display: flex;
    align-items: center;
    gap: 12px;
    border: 1px solid #242c38;
    border-radius: 8px;
    background: #101722;
    padding: 14px 16px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .taskCompleting {
    opacity: 0.4;
    transform: translateX(8px);
    text-decoration: line-through;
    color: #8b98aa;
    border-color: rgba(46, 204, 113, 0.3);
    background: rgba(46, 204, 113, 0.03);
  }

  .taskCheckbox {
    width: 22px;
    height: 22px;
    border: 2px solid #3c495e;
    border-radius: 50%;
    background: #080b10;
    cursor: pointer;
    padding: 0;
    display: grid;
    place-items: center;
    color: #2ecc71;
    transition: all 0.2s;
  }

  .taskCheckbox:hover {
    border-color: #2ecc71;
    background: rgba(46, 204, 113, 0.05);
  }

  .taskCheckbox.checked {
    border-color: #2ecc71;
    background: rgba(46, 204, 113, 0.15);
  }

  .taskContent {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .taskTitle {
    font-weight: 500;
    overflow-wrap: anywhere;
  }

  .taskDueDate {
    font-size: 0.76rem;
    color: #e67e22;
    margin-top: 4px;
  }
</style>
