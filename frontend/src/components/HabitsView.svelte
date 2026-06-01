<script>
  import { onMount } from 'svelte'
  import Icons from './Icons.svelte'

  const API_BASE = import.meta.env.DEV ? 'http://127.0.0.1:5000' : ''
  const WEEKS_TO_SHOW = 30

  let habits = $state([])
  let newHabitName = $state('')
  let isLoading = $state(true)
  let isSaving = $state(false)
  let error = $state('')

  function dateKey(day) {
    const year = day.getFullYear()
    const month = String(day.getMonth() + 1).padStart(2, '0')
    const date = String(day.getDate()).padStart(2, '0')
    return `${year}-${month}-${date}`
  }

  const todayKey = dateKey(new Date())
  const months = $derived.by(() => {
    const list = []
    const today = new Date()
    const currentYear = today.getFullYear()
    const currentMonth = today.getMonth()
    
    const numMonths = 6
    
    for (let i = numMonths - 1; i >= 0; i--) {
      let targetMonth = currentMonth - i
      let targetYear = currentYear
      while (targetMonth < 0) {
        targetMonth += 12
        targetYear -= 1
      }
      
      const firstDay = new Date(targetYear, targetMonth, 1)
      const lastDay = new Date(targetYear, targetMonth + 1, 0)
      
      const firstDayOfWeek = firstDay.getDay()
      const startPadCount = firstDayOfWeek === 0 ? 6 : firstDayOfWeek - 1
      
      const monthDays = []
      
      for (let p = 0; p < startPadCount; p++) {
        monthDays.push({ isPlaceholder: true })
      }
      
      const numDays = lastDay.getDate()
      for (let d = 1; d <= numDays; d++) {
        const dateObj = new Date(targetYear, targetMonth, d)
        monthDays.push({
          isPlaceholder: false,
          date: dateKey(dateObj),
          label: new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short' }).format(dateObj)
        })
      }
      
      const lastDayOfWeek = lastDay.getDay()
      const endPadCount = lastDayOfWeek === 0 ? 0 : 7 - lastDayOfWeek
      for (let p = 0; p < endPadCount; p++) {
        monthDays.push({ isPlaceholder: true })
      }
      
      const weeksList = []
      for (let w = 0; w < monthDays.length; w += 7) {
        weeksList.push(monthDays.slice(w, w + 7))
      }
      
      const monthName = new Intl.DateTimeFormat('en-IN', { month: 'short', year: 'numeric' }).format(firstDay)
      
      list.push({
        name: monthName,
        weeks: weeksList
      })
    }
    
    return list
  })

  async function request(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
      ...options,
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      throw new Error(payload.error ?? 'Habit request failed')
    }

    return response.json()
  }

  async function loadHabits() {
    isLoading = true
    error = ''

    try {
      const payload = await request('/api/habits')
      habits = payload.habits ?? []
    } catch (err) {
      error = err.message
    } finally {
      isLoading = false
    }
  }

  async function addHabit() {
    const name = newHabitName.trim()
    if (!name || isSaving) return

    isSaving = true
    error = ''

    try {
      const payload = await request('/api/habits', {
        method: 'POST',
        body: JSON.stringify({ name }),
      })
      habits = [payload.habit, ...habits]
      newHabitName = ''
    } catch (err) {
      error = err.message
    } finally {
      isSaving = false
    }
  }

  async function adjustHabit(habitId, direction) {
    error = ''

    try {
      const payload = await request(`/api/habits/${habitId}/${direction}`, { method: 'POST' })
      habits = habits.map((habit) => {
        if (habit.id !== habitId) return habit

        const completions = habit.completions.filter((completion) => completion.date !== payload.date)
        if (payload.count > 0) {
          completions.push({ date: payload.date, count: payload.count })
        }

        return { ...habit, completions }
      })
    } catch (err) {
      error = err.message
    }
  }

  function countForDate(habit, date) {
    return habit.completions.find((completion) => completion.date === date)?.count ?? 0
  }

  function todayCount(habit) {
    return countForDate(habit, todayKey)
  }

  function heatStyle(count) {
    if (count <= 0) return 'background: #202734; border-color: #303946; opacity: 1;'

    const opacity = Math.min(0.35 + count * 0.13, 1)
    return `background: rgba(46, 204, 113, ${opacity}); border-color: rgba(75, 224, 132, ${Math.min(opacity + 0.12, 1)});`
  }

  onMount(() => {
    loadHabits()

    const handleTaskCompleted = () => {
      loadHabits()
    }
    window.addEventListener('task-completed', handleTaskCompleted)

    return () => {
      window.removeEventListener('task-completed', handleTaskCompleted)
    }
  })
</script>

<section class="panel scrollPanel habitsPanel">
  <div class="sectionHeader">
    <h2>+ Daily Habits</h2>
    <span class="statusPill">SQLite ledger</span>
  </div>

  <form class="inlineForm" onsubmit={(event) => { event.preventDefault(); addHabit() }}>
    <input bind:value={newHabitName} type="text" placeholder="New habit" aria-label="New habit name" />
    <button type="submit" disabled={isSaving}>{isSaving ? 'Adding' : 'Add'}</button>
  </form>

  {#if error}
    <p class="errorText">{error}</p>
  {/if}

  {#if isLoading}
    <div class="emptyState">Loading habits...</div>
  {:else if habits.length === 0}
    <div class="emptyState">No habits yet.</div>
  {:else}
    <div class="habitList">
      {#each habits as habit (habit.id)}
        <article class="habitRow">
          <div class="habitInfo">
            <strong>{habit.name}</strong>
            <span>{todayCount(habit)} today</span>
          </div>

          <div class="habitControls" aria-label={`${habit.name} controls`}>
            <button type="button" title="Decrease today" onclick={() => adjustHabit(habit.id, 'decrement')}>
              <Icons name="minus" size={14} />
            </button>
            <button type="button" title="Increase today" onclick={() => adjustHabit(habit.id, 'increment')}>
              <Icons name="plus" size={14} />
            </button>
          </div>

          <div class="monthsContainer">
            {#each months as month}
              <div class="monthBlock">
                <header class="monthBlockHeader" aria-hidden="true">
                  {month.name}
                </header>
                <div class="monthGrid" aria-label={`${habit.name} ${month.name}`}>
                  {#each month.weeks as week}
                    <div class="heatmapWeek">
                      {#each week as day}
                        {#if day.isPlaceholder}
                          <span class="heatCell placeholder" aria-hidden="true"></span>
                        {:else}
                          {@const count = countForDate(habit, day.date)}
                          <span
                            class="heatCell"
                            class:today={day.date === todayKey}
                            style={heatStyle(count)}
                            title={`${day.label}: ${count}`}
                            aria-label={`${day.label}: ${count}`}
                          ></span>
                        {/if}
                      {/each}
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        </article>
      {/each}
    </div>
  {/if}
</section>
