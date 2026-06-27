<script>
  import { onMount, onDestroy } from 'svelte'
  import Icons from './Icons.svelte'

  const API_BASE = import.meta.env.DEV ? 'http://127.0.0.1:5000' : ''

  let { isActive = false } = $props()

  // Timer states
  let timerState = $state('idle') // 'idle', 'running', 'paused'

  $effect(() => {
    if (isActive) {
      syncElapsed()
    }
  })
  let elapsedTime = $state(0)
  let activeTopic = $state('Study') // 'Study', 'Gaming', 'Timepass'
  let startTime = $state('')

  let sessions = $state([])
  let isLoading = $state(true)
  let error = $state('')
  let isSaving = $state(false)

  // Chart toggles
  let historyViewMode = $state('weekly') // 'weekly', 'monthly'

  let intervalId = null

  // Dropdown options
  const topics = ['Study', 'Gaming', 'Timepass', 'Productive']

  // Date helper
  function getTodayDateString() {
    const d = new Date()
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const date = String(d.getDate()).padStart(2, '0')
    return `${year}-${month}-${date}`
  }

  function getLocalISOString(date = new Date()) {
    const pad = (num) => String(num).padStart(2, '0')
    const year = date.getFullYear()
    const month = pad(date.getMonth() + 1)
    const day = pad(date.getDate())
    const hours = pad(date.getHours())
    const minutes = pad(date.getMinutes())
    const seconds = pad(date.getSeconds())
    return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`
  }

  function parseLocalDate(dateStr) {
    if (!dateStr) return new Date()
    const [y, m, d] = dateStr.split('-').map(Number)
    return new Date(y, m - 1, d)
  }

  // Format seconds to HH:MM:SS
  function formatTime(totalSeconds) {
    const hrs = String(Math.floor(totalSeconds / 3600)).padStart(2, '0')
    const mins = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0')
    const secs = String(totalSeconds % 60).padStart(2, '0')
    return `${hrs}:${mins}:${secs}`
  }

  // Format duration to user-friendly text (e.g. "1h 24m")
  function formatDurationText(totalSeconds) {
    if (totalSeconds < 60) return `${totalSeconds}s`
    const hrs = Math.floor(totalSeconds / 3600)
    const mins = Math.floor((totalSeconds % 3600) / 60)
    if (hrs > 0) {
      return `${hrs}h ${mins}m`
    }
    return `${mins}m`
  }

  async function request(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
      ...options,
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      throw new Error(payload.error ?? 'Request failed')
    }

    return response.json()
  }

  async function loadSessions() {
    isLoading = true
    error = ''
    try {
      const payload = await request('/api/focus/sessions')
      sessions = payload.sessions ?? []
    } catch (err) {
      error = err.message
    } finally {
      isLoading = false
    }
  }

  // Synchronize elapsed seconds with system clock
  function syncElapsed() {
    if (timerState === 'running' && startTime) {
      elapsedTime = Math.max(0, Math.floor((Date.now() - new Date(startTime).getTime()) / 1000))
      localStorage.setItem('wallsync_timer_elapsed', String(elapsedTime))
    }
  }

  // Timer Tick Trigger
  function tick() {
    if (timerState === 'running') {
      syncElapsed()
    } else {
      elapsedTime++
    }
  }

  function startTimer() {
    if (timerState === 'running') return

    timerState = 'running'
    startTime = getLocalISOString()
    elapsedTime = 0

    // Store state in localStorage for persistent background tick
    localStorage.setItem('wallsync_timer_state', 'running')
    localStorage.setItem('wallsync_timer_start', startTime)
    localStorage.setItem('wallsync_timer_topic', activeTopic)

    intervalId = setInterval(tick, 1000)
  }

  function pauseTimer() {
    if (timerState !== 'running') return

    clearInterval(intervalId)
    timerState = 'paused'

    localStorage.setItem('wallsync_timer_state', 'paused')
    localStorage.setItem('wallsync_timer_elapsed', String(elapsedTime))
  }

  function resumeTimer() {
    if (timerState !== 'paused') return

    timerState = 'running'
    
    // Readjust start time based on elapsed seconds so refresh recalculates correctly
    const newStart = new Date(Date.now() - elapsedTime * 1000)
    startTime = getLocalISOString(newStart)

    localStorage.setItem('wallsync_timer_state', 'running')
    localStorage.setItem('wallsync_timer_start', startTime)

    intervalId = setInterval(tick, 1000)
  }

  async function stopTimer() {
    if (timerState === 'idle') return

    clearInterval(intervalId)
    const endTime = getLocalISOString()
    const sessionDuration = elapsedTime

    isSaving = true
    error = ''

    try {
      const payload = await request('/api/focus/sessions', {
        method: 'POST',
        body: JSON.stringify({
          topic: activeTopic,
          start_time: startTime,
          end_time: endTime,
          duration_seconds: sessionDuration,
        }),
      })

      if (payload.sessions) {
        sessions = [...payload.sessions, ...sessions]
      } else if (payload.session) {
        sessions = [payload.session, ...sessions]
      }
      resetTimerState()
    } catch (err) {
      error = err.message
      isSaving = false
    }
  }

  function resetTimer() {
    if (confirm('Are you sure you want to cancel the current study session? It will not be logged.')) {
      resetTimerState()
    }
  }

  function resetTimerState() {
    clearInterval(intervalId)
    timerState = 'idle'
    elapsedTime = 0
    isSaving = false

    // Clear local storage
    localStorage.removeItem('wallsync_timer_state')
    localStorage.removeItem('wallsync_timer_start')
    localStorage.removeItem('wallsync_timer_elapsed')
    localStorage.removeItem('wallsync_timer_topic')
  }

  async function deleteSession(sessionId) {
    if (!confirm('Are you sure you want to delete this session?')) return

    try {
      await request(`/api/focus/sessions/${sessionId}`, { method: 'DELETE' })
      sessions = sessions.filter((s) => s.id !== sessionId)
    } catch (err) {
      error = err.message
    }
  }

  // Load persistent timer state on mount
  onMount(() => {
    loadSessions()

    const savedState = localStorage.getItem('wallsync_timer_state')
    if (savedState === 'running') {
      const savedStart = localStorage.getItem('wallsync_timer_start')
      const savedTopic = localStorage.getItem('wallsync_timer_topic')
      if (savedStart && savedTopic) {
        startTime = savedStart
        activeTopic = savedTopic
        timerState = 'running'
        
        // Calculate offset difference
        const startMs = new Date(startTime).getTime()
        elapsedTime = Math.max(0, Math.floor((Date.now() - startMs) / 1000))
        
        intervalId = setInterval(tick, 1000)
      }
    } else if (savedState === 'paused') {
      const savedElapsed = localStorage.getItem('wallsync_timer_elapsed')
      const savedTopic = localStorage.getItem('wallsync_timer_topic')
      const savedStart = localStorage.getItem('wallsync_timer_start')
      if (savedElapsed && savedTopic && savedStart) {
        startTime = savedStart
        activeTopic = savedTopic
        elapsedTime = parseInt(savedElapsed)
        timerState = 'paused'
      }
    }

    // Listen for tab focus/visibility change to recalibrate elapsed timer
    window.addEventListener('focus', syncElapsed)
    document.addEventListener('visibilitychange', syncElapsed)
  })

  onDestroy(() => {
    if (intervalId) clearInterval(intervalId)
    window.removeEventListener('focus', syncElapsed)
    document.removeEventListener('visibilitychange', syncElapsed)
  })

  // Reactive dashboard metrics
  const todayDateStr = $derived(getTodayDateString())
  const todaySessions = $derived(sessions.filter((s) => s.session_date === todayDateStr))
  
  const todayTotalSeconds = $derived(todaySessions.reduce((acc, s) => acc + s.duration_seconds, 0))

  const todaySecondsByTopic = $derived.by(() => {
    const dict = { Study: 0, Gaming: 0, Timepass: 0, Productive: 0 }
    todaySessions.forEach((s) => {
      if (dict[s.topic] !== undefined) {
        dict[s.topic] += s.duration_seconds
      }
    })
    return dict
  })

  // Calculate streak based on study logs
  const streakDays = $derived.by(() => {
    const studyDates = new Set(
      sessions.filter((s) => s.topic === 'Study').map((s) => s.session_date)
    )
    if (studyDates.size === 0) return 0

    let streak = 0
    let checkDate = new Date()
    
    // Check backwards from today
    while (true) {
      const year = checkDate.getFullYear()
      const month = String(checkDate.getMonth() + 1).padStart(2, '0')
      const date = String(checkDate.getDate()).padStart(2, '0')
      const dateStr = `${year}-${month}-${date}`

      if (studyDates.has(dateStr)) {
        streak++
        checkDate.setDate(checkDate.getDate() - 1)
      } else {
        // If today is missed but yesterday had a study log, streak is still active
        if (streak === 0) {
          const yesterday = new Date()
          yesterday.setDate(yesterday.getDate() - 1)
          const yYear = yesterday.getFullYear()
          const yMonth = String(yesterday.getMonth() + 1).padStart(2, '0')
          const yDate = String(yesterday.getDate()).padStart(2, '0')
          const yDateStr = `${yYear}-${yMonth}-${yDate}`

          if (studyDates.has(yDateStr)) {
            checkDate.setDate(checkDate.getDate() - 1)
            continue
          }
        }
        break
      }
    }
    return streak
  })

  // Derived weekly chart data
  const weeklyData = $derived.by(() => {
    const list = []
    const today = new Date()
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today)
      d.setDate(today.getDate() - i)
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const date = String(d.getDate()).padStart(2, '0')
      const dateStr = `${year}-${month}-${date}`

      const label = new Intl.DateTimeFormat('en-IN', { weekday: 'short' }).format(d)
      const daySessions = sessions.filter((s) => s.session_date === dateStr)
      
      const study = daySessions.filter((s) => s.topic === 'Study').reduce((acc, s) => acc + s.duration_seconds, 0)
      const gaming = daySessions.filter((s) => s.topic === 'Gaming').reduce((acc, s) => acc + s.duration_seconds, 0)
      const timepass = daySessions.filter((s) => s.topic === 'Timepass').reduce((acc, s) => acc + s.duration_seconds, 0)
      const productive = daySessions.filter((s) => s.topic === 'Productive').reduce((acc, s) => acc + s.duration_seconds, 0)

      list.push({ label, Study: study, Gaming: gaming, Timepass: timepass, Productive: productive })
    }
    return list
  })

  // Derived monthly chart data (past 4 weeks)
  const monthlyData = $derived.by(() => {
    const list = []
    const today = new Date()
    for (let w = 3; w >= 0; w--) {
      const startDay = new Date(today)
      startDay.setDate(today.getDate() - (w * 7 + 6))
      startDay.setHours(0, 0, 0, 0)

      const endDay = new Date(today)
      endDay.setDate(today.getDate() - (w * 7))
      endDay.setHours(23, 59, 59, 999)

      const label = `${new Intl.DateTimeFormat('en-IN', { month: 'short', day: '2-digit' }).format(startDay)} - ${new Intl.DateTimeFormat('en-IN', { day: '2-digit' }).format(endDay)}`
      
      const weekSessions = sessions.filter((s) => {
        const sDate = parseLocalDate(s.session_date)
        return sDate >= startDay && sDate <= endDay
      })

      const study = weekSessions.filter((s) => s.topic === 'Study').reduce((acc, s) => acc + s.duration_seconds, 0)
      const gaming = weekSessions.filter((s) => s.topic === 'Gaming').reduce((acc, s) => acc + s.duration_seconds, 0)
      const timepass = weekSessions.filter((s) => s.topic === 'Timepass').reduce((acc, s) => acc + s.duration_seconds, 0)
      const productive = weekSessions.filter((s) => s.topic === 'Productive').reduce((acc, s) => acc + s.duration_seconds, 0)

      list.push({ label, Study: study, Gaming: gaming, Timepass: timepass, Productive: productive })
    }
    return list
  })

  // Determine max duration for chart scaling
  const chartData = $derived(historyViewMode === 'weekly' ? weeklyData : monthlyData)
  const maxSessionSeconds = $derived.by(() => {
    const maxVal = Math.max(...chartData.map((d) => d.Study + d.Gaming + d.Timepass + d.Productive), 0)
    return maxVal === 0 ? 3600 : maxVal // default 1 hour scale if all empty
  })
</script>

<section class="panel scrollPanel focusPanel">
  <!-- Section Header -->
  <div class="sectionHeader">
    <h2>⌛ Focus Tracker</h2>
    <span class="statusPill">Session Ledger</span>
  </div>

  {#if error}
    <p class="errorText">{error}</p>
  {/if}

  <div class="focusDashboard">
    <!-- TIMER PANEL -->
    <div class="timerCard glassPanel">
      <div class="timerHeader">
        <h3>Focus Stopwatch</h3>
        <select bind:value={activeTopic} disabled={timerState !== 'idle'} class="topicSelect">
          {#each topics as topic}
            <option value={topic}>{topic}</option>
          {/each}
        </select>
      </div>

      <div class="stopwatchDisplay">
        <span class="elapsedText">{formatTime(elapsedTime)}</span>
        <span class="activeTag" class:tag-study={activeTopic === 'Study'} class:tag-gaming={activeTopic === 'Gaming'} class:tag-timepass={activeTopic === 'Timepass'} class:tag-productive={activeTopic === 'Productive'}>
          {activeTopic}
        </span>
      </div>

      <div class="timerControls">
        {#if timerState === 'idle'}
          <button class="controlBtn startBtn" onclick={startTimer}>
            <Icons name="plus" size={16} /> Start Focus
          </button>
        {:else if timerState === 'running'}
          <button class="controlBtn pauseBtn" onclick={pauseTimer}>
            <Icons name="minus" size={16} /> Pause
          </button>
          <button class="controlBtn stopBtn" onclick={stopTimer} disabled={isSaving}>
            <Icons name="check" size={16} /> {isSaving ? 'Logging...' : 'Stop & Log'}
          </button>
        {:else}
          <button class="controlBtn startBtn" onclick={resumeTimer}>
            <Icons name="plus" size={16} /> Resume
          </button>
          <button class="controlBtn stopBtn" onclick={stopTimer} disabled={isSaving}>
            <Icons name="check" size={16} /> Stop & Log
          </button>
          <button class="controlBtn cancelBtn" onclick={resetTimer}>
            Cancel
          </button>
        {/if}
      </div>
    </div>

    <!-- METRICS OVERVIEW -->
    <div class="metricsSummary">
      <!-- Cards Grid -->
      <div class="cardsGrid">
        <div class="metricCard glassPanel">
          <span class="cardLabel">Today's Focus</span>
          <strong class="cardValue">{formatDurationText(todayTotalSeconds)}</strong>
        </div>
        <div class="metricCard glassPanel">
          <span class="cardLabel">Study Streak</span>
          <strong class="cardValue">{streakDays} Days</strong>
        </div>
        <div class="metricCard glassPanel">
          <span class="cardLabel">Session Count</span>
          <strong class="cardValue">{todaySessions.length} Logged</strong>
        </div>
      </div>

      <!-- Topic Proportional Bar -->
      <div class="proportionalBarCard glassPanel">
        <h4>Today's Allocation</h4>
        <div class="allocationBar">
          {#if todayTotalSeconds === 0}
            <div class="emptyBar">No active logs logged today.</div>
          {:else}
            {#if todaySecondsByTopic.Study > 0}
              <div class="barSegment seg-study" style="flex-grow: {todaySecondsByTopic.Study}" title={`Study: ${formatDurationText(todaySecondsByTopic.Study)}`}></div>
            {/if}
            {#if todaySecondsByTopic.Gaming > 0}
              <div class="barSegment seg-gaming" style="flex-grow: {todaySecondsByTopic.Gaming}" title={`Gaming: ${formatDurationText(todaySecondsByTopic.Gaming)}`}></div>
            {/if}
            {#if todaySecondsByTopic.Timepass > 0}
              <div class="barSegment seg-timepass" style="flex-grow: {todaySecondsByTopic.Timepass}" title={`Timepass: ${formatDurationText(todaySecondsByTopic.Timepass)}`}></div>
            {/if}
            {#if todaySecondsByTopic.Productive > 0}
              <div class="barSegment seg-productive" style="flex-grow: {todaySecondsByTopic.Productive}" title={`Productive: ${formatDurationText(todaySecondsByTopic.Productive)}`}></div>
            {/if}
          {/if}
        </div>
        <div class="barLabels">
          <span class="barLegend studyLegend">Study ({formatDurationText(todaySecondsByTopic.Study)})</span>
          <span class="barLegend gamingLegend">Gaming ({formatDurationText(todaySecondsByTopic.Gaming)})</span>
          <span class="barLegend timepassLegend">Timepass ({formatDurationText(todaySecondsByTopic.Timepass)})</span>
          <span class="barLegend productiveLegend">Productive ({formatDurationText(todaySecondsByTopic.Productive)})</span>
        </div>
      </div>
    </div>
  </div>

  <!-- HISTORICAL TIMELINE CHART -->
  <div class="chartCard glassPanel">
    <div class="chartHeader">
      <h3>Activity Timeline</h3>
      <div class="toggleGroup">
        <button class="toggleBtn" class:active={historyViewMode === 'weekly'} onclick={() => historyViewMode = 'weekly'}>Weekly</button>
        <button class="toggleBtn" class:active={historyViewMode === 'monthly'} onclick={() => historyViewMode = 'monthly'}>Monthly</button>
      </div>
    </div>

    <div class="chartCanvas">
      {#each chartData as item}
        {@const sumSeconds = item.Study + item.Gaming + item.Timepass + item.Productive}
        {@const barHeightPct = (sumSeconds / maxSessionSeconds) * 100}
        <div class="chartColumnWrapper">
          <div class="chartColumnBar" style="height: {Math.max(5, barHeightPct)}%">
            {#if sumSeconds > 0}
              {#if item.Study > 0}
                <div class="chartSegment seg-study" style="height: {(item.Study / sumSeconds) * 100}%" title={`Study: ${formatDurationText(item.Study)}`}></div>
              {/if}
              {#if item.Gaming > 0}
                <div class="chartSegment seg-gaming" style="height: {(item.Gaming / sumSeconds) * 100}%" title={`Gaming: ${formatDurationText(item.Gaming)}`}></div>
              {/if}
              {#if item.Timepass > 0}
                <div class="chartSegment seg-timepass" style="height: {(item.Timepass / sumSeconds) * 100}%" title={`Timepass: ${formatDurationText(item.Timepass)}`}></div>
              {/if}
              {#if item.Productive > 0}
                <div class="chartSegment seg-productive" style="height: {(item.Productive / sumSeconds) * 100}%" title={`Productive: ${formatDurationText(item.Productive)}`}></div>
              {/if}
            {/if}
          </div>
          <span class="columnLabel">{item.label}</span>
        </div>
      {/each}
    </div>
  </div>

  <!-- HISTORICAL SESSION LEDGER -->
  <div class="ledgerCard glassPanel">
    <h3>Focus History</h3>
    {#if isLoading}
      <div class="emptyState">Retrieving focus logs...</div>
    {:else if sessions.length === 0}
      <div class="emptyState">No study sessions logged yet. Log your first focus session!</div>
    {:else}
      <div class="ledgerTable">
        <div class="ledgerHeaderRow">
          <span>Date</span>
          <span>Topic</span>
          <span>Duration</span>
          <span>Actions</span>
        </div>
        <div class="ledgerRowsScroll">
          {#each sessions as session (session.id)}
            <div class="ledgerRow">
              <span class="ledgerDate">
                {new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }).format(parseLocalDate(session.session_date))}
              </span>
              <span class="ledgerTopic">
                <span class="topicTag" class:tag-study={session.topic === 'Study'} class:tag-gaming={session.topic === 'Gaming'} class:tag-timepass={session.topic === 'Timepass'} class:tag-productive={session.topic === 'Productive'}>
                  {session.topic}
                </span>
              </span>
              <span class="ledgerDuration">{formatDurationText(session.duration_seconds)}</span>
              <span class="ledgerActions">
                <button type="button" class="deleteLogBtn" onclick={() => deleteSession(session.id)} title="Delete log">
                  ✕
                </button>
              </span>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  </div>
</section>

<style>
  .focusPanel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .focusDashboard {
    display: grid;
    grid-template-columns: minmax(280px, 360px) 1fr;
    gap: 16px;
  }

  @media (max-width: 820px) {
    .focusDashboard {
      grid-template-columns: 1fr;
    }
  }

  .glassPanel {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    background: rgba(16, 23, 34, 0.55);
    padding: 16px;
  }

  /* Timer styling */
  .timerCard {
    display: flex;
    flex-direction: column;
    gap: 20px;
    align-items: center;
  }

  .timerHeader {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .timerHeader h3 {
    margin: 0;
    font-size: 1.05rem;
    color: #eef2f8;
  }

  .topicSelect {
    border: 1px solid #2b3544;
    border-radius: 6px;
    background: #090d14;
    color: #eef2f8;
    padding: 4px 8px;
    font-size: 0.85rem;
  }

  .stopwatchDisplay {
    width: 190px;
    height: 190px;
    border-radius: 50%;
    border: 4px solid #1c2635;
    background: #090d14;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    box-shadow: inset 0 0 20px rgba(0,0,0,0.6);
  }

  .elapsedText {
    font-size: 2.1rem;
    font-weight: 750;
    color: #ffffff;
    font-family: monospace;
    letter-spacing: 1px;
  }

  .activeTag {
    font-size: 0.72rem;
    padding: 2px 8px;
    border-radius: 99px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .tag-study {
    background: rgba(46, 204, 113, 0.15);
    color: #2ecc71;
    border: 1px solid rgba(46, 204, 113, 0.3);
  }
  .tag-gaming {
    background: rgba(230, 126, 34, 0.15);
    color: #e67e22;
    border: 1px solid rgba(230, 126, 34, 0.3);
  }
  .tag-timepass {
    background: rgba(231, 76, 60, 0.15);
    color: #e74c3c;
    border: 1px solid rgba(231, 76, 60, 0.3);
  }
  .tag-productive {
    background: rgba(52, 152, 219, 0.15);
    color: #3498db;
    border: 1px solid rgba(52, 152, 219, 0.3);
  }

  .timerControls {
    width: 100%;
    display: flex;
    gap: 8px;
    justify-content: center;
  }

  .controlBtn {
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: 650;
    font-size: 0.88rem;
    display: flex;
    align-items: center;
    gap: 6px;
    border: none;
    transition: all 0.2s;
  }

  .startBtn {
    background: #27ae60;
    color: white;
  }
  .startBtn:hover {
    background: #2ecc71;
  }

  .pauseBtn {
    background: #d35400;
    color: white;
  }
  .pauseBtn:hover {
    background: #e67e22;
  }

  .stopBtn {
    background: #1d4f86;
    color: white;
    border: 1px solid #4a8dd8;
  }
  .stopBtn:hover:not(:disabled) {
    background: #224067;
  }

  .cancelBtn {
    background: transparent;
    color: #8b98aa;
    border: 1px solid #2b3544;
  }
  .cancelBtn:hover {
    color: white;
    background: rgba(255, 255, 255, 0.05);
  }

  /* Metrics Summary layout */
  .metricsSummary {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .cardsGrid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }

  @media (max-width: 480px) {
    .cardsGrid {
      grid-template-columns: 1fr;
    }
  }

  .metricCard {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 14px;
  }

  .cardLabel {
    font-size: 0.78rem;
    color: #8b98aa;
  }

  .cardValue {
    font-size: 1.4rem;
    font-weight: 700;
    color: #ffffff;
  }

  /* Allocation Progress Bar */
  .proportionalBarCard h4 {
    margin: 0 0 12px;
    font-size: 0.95rem;
    color: #eef2f8;
  }

  .allocationBar {
    height: 12px;
    background: #141c29;
    border-radius: 99px;
    overflow: hidden;
    display: flex;
    margin-bottom: 12px;
  }

  .emptyBar {
    width: 100%;
    font-size: 0.78rem;
    color: #5d6d7e;
    text-align: center;
    line-height: 12px;
  }

  .barSegment {
    height: 100%;
    transition: all 0.3s;
  }

  .seg-study {
    background: #2ecc71;
  }
  .seg-gaming {
    background: #e67e22;
  }
  .seg-timepass {
    background: #e74c3c;
  }
  .seg-productive {
    background: #3498db;
  }

  .barLabels {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .barLegend {
    font-size: 0.72rem;
    display: flex;
    align-items: center;
    gap: 5px;
    font-weight: 500;
  }
  .barLegend::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
  }
  .studyLegend::before {
    background: #2ecc71;
  }
  .gamingLegend::before {
    background: #e67e22;
  }
  .timepassLegend::before {
    background: #e74c3c;
  }
  .productiveLegend::before {
    background: #3498db;
  }
  .studyLegend { color: #2ecc71; }
  .gamingLegend { color: #e67e22; }
  .timepassLegend { color: #e74c3c; }
  .productiveLegend { color: #3498db; }

  /* Chart Layouts */
  .chartHeader {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  
  .chartHeader h3 {
    margin: 0;
    font-size: 1.05rem;
    color: #eef2f8;
  }

  .toggleGroup {
    display: flex;
    border: 1px solid #2b3544;
    border-radius: 6px;
    overflow: hidden;
  }

  .toggleBtn {
    background: #090d14;
    color: #8b98aa;
    border: none;
    padding: 4px 12px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
  }

  .toggleBtn.active {
    background: #1d4f86;
    color: white;
  }

  .chartCanvas {
    height: 180px;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 8px;
    border-bottom: 1px solid #2b3544;
    padding-bottom: 6px;
    margin-top: 24px;
  }

  .chartColumnWrapper {
    flex: 1;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    align-items: center;
    gap: 6px;
  }

  .chartColumnBar {
    width: 60%;
    max-width: 32px;
    min-width: 14px;
    background: #141c29;
    border-radius: 4px 4px 0 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
  }

  .chartSegment {
    width: 100%;
    transition: all 0.3s;
  }

  .columnLabel {
    font-size: 0.72rem;
    color: #8b98aa;
    white-space: nowrap;
  }

  /* Session Ledger Table */
  .ledgerCard h3 {
    margin: 0 0 12px;
    font-size: 1.05rem;
    color: #eef2f8;
  }

  .ledgerTable {
    display: flex;
    flex-direction: column;
    border: 1px solid #242c38;
    border-radius: 8px;
    background: #090d14;
    overflow: hidden;
  }

  .ledgerHeaderRow {
    display: grid;
    grid-template-columns: 1.5fr 1fr 1fr auto;
    padding: 10px 14px;
    background: #101722;
    border-bottom: 1px solid #242c38;
    font-size: 0.78rem;
    font-weight: 650;
    color: #8b98aa;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .ledgerRowsScroll {
    max-height: 220px;
    overflow-y: auto;
  }

  .ledgerRow {
    display: grid;
    grid-template-columns: 1.5fr 1fr 1fr auto;
    padding: 10px 14px;
    align-items: center;
    border-bottom: 1px solid #192231;
    font-size: 0.88rem;
    color: #eef2f8;
  }

  .ledgerRow:last-child {
    border-bottom: none;
  }

  .topicTag {
    font-size: 0.72rem;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
  }

  .deleteLogBtn {
    background: transparent;
    color: #e74c3c;
    border: none;
    cursor: pointer;
    font-size: 0.95rem;
    padding: 4px;
    display: grid;
    place-items: center;
    transition: all 0.2s;
  }

  .deleteLogBtn:hover {
    color: #ff6b6b;
    transform: scale(1.15);
  }
</style>
