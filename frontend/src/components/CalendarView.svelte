<script>
  import { onMount } from 'svelte'
  import Icons from './Icons.svelte'

  const API_BASE = import.meta.env.DEV ? 'http://127.0.0.1:5000' : ''

  let events = $state([])
  let isLoading = $state(true)
  let error = $state('')

  async function loadEvents() {
    isLoading = true
    error = ''
    try {
      const response = await fetch(`${API_BASE}/api/calendar/events`)
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.error ?? 'Calendar request failed')
      }
      const payload = await response.json()
      events = payload.events ?? []
    } catch (err) {
      error = err.message
    } finally {
      isLoading = false
    }
  }

  // Group events by day for standard agenda styling
  const groupedEvents = $derived.by(() => {
    const groups = {}
    
    events.forEach(event => {
      const startDate = new Date(event.start)
      const dayKey = startDate.toDateString() // "Fri May 22 2026"
      
      if (!groups[dayKey]) {
        groups[dayKey] = {
          date: startDate,
          label: getDayLabel(startDate),
          items: []
        }
      }
      groups[dayKey].items.push(event)
    })
    
    return Object.values(groups).sort((a, b) => a.date - b.date)
  })

  function getDayLabel(date) {
    const today = new Date()
    const tomorrow = new Date()
    tomorrow.setDate(today.getDate() + 1)
    
    today.setHours(0, 0, 0, 0)
    tomorrow.setHours(0, 0, 0, 0)
    
    const target = new Date(date)
    target.setHours(0, 0, 0, 0)
    
    if (target.getTime() === today.getTime()) {
      return '★ Today'
    } else if (target.getTime() === tomorrow.getTime()) {
      return 'Tomorrow'
    }
    
    return new Intl.DateTimeFormat('en-IN', { weekday: 'short', day: '2-digit', month: 'short' }).format(date)
  }

  function formatTimeRange(startIso, endIso) {
    const start = new Date(startIso)
    const end = new Date(endIso)
    
    const timeFormat = new Intl.DateTimeFormat('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    })
    
    // Check if it's an all-day event (start and end have 00:00:00)
    const isAllDay = start.getHours() === 0 && start.getMinutes() === 0 && 
                      end.getHours() === 0 && end.getMinutes() === 0 &&
                      (end - start) % 86400000 === 0;

    if (isAllDay) return 'All Day'
    
    return `${timeFormat.format(start)} - ${timeFormat.format(end)}`
  }

  onMount(loadEvents)
</script>

<section class="panel scrollPanel calendarPanel">
  <div class="sectionHeader">
    <h2>□ Agenda Feed</h2>
    <button class="refreshButton" aria-label="Refresh events" onclick={loadEvents} disabled={isLoading}>
      <Icons name="agent" size={14} class={isLoading ? 'spinning' : ''} />
    </button>
  </div>

  {#if error}
    <div class="calendarConfigCard">
      <div class="configIconWrapper">
        <Icons name="info" size={32} />
      </div>
      <h3>Google Calendar Not Fully Connected</h3>
      <p>Could not fetch your private ICS feed. Make sure your calendar setup is correct.</p>
      <div class="configGuide">
        <strong>Google ICS URL Configuration:</strong>
        <ol>
          <li>Open Google Calendar on your PC.</li>
          <li>Click Settings &gt; Settings for my calendars.</li>
          <li>Scroll to the bottom to find **"Secret address in iCal format"**.</li>
          <li>Copy that secret `.ics` link.</li>
          <li>Open your `.env` file in the WallSync root directory and paste it:
            <code>GOOGLE_ICS_URL=https://calendar.google.com/.../basic.ics</code>
          </li>
          <li>Restart your Flask backend and try again.</li>
        </ol>
      </div>
      <button class="setupRetryButton" type="button" onclick={loadEvents}>Retry Fetch</button>
    </div>
  {:else if isLoading}
    <div class="emptyState">Syncing events from your private Google Calendar feed...</div>
  {:else if events.length === 0}
    <div class="emptyState">No upcoming events found for the next 30 days.</div>
  {:else}
    <div class="agendaTimeline">
      {#each groupedEvents as group}
        <div class="agendaDayGroup">
          <h3 class="agendaDayHeader">{group.label}</h3>
          <div class="agendaDayItems">
            {#each group.items as event}
              <article class="eventCard">
                <div class="eventTimeBar"></div>
                <div class="eventBody">
                  <span class="eventTime">{formatTimeRange(event.start, event.end)}</span>
                  <strong class="eventSummary">{event.summary}</strong>
                  {#if event.location}
                    <span class="eventLocation">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="locationIcon"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
                      {event.location}
                    </span>
                  {/if}
                </div>
              </article>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .calendarPanel {
    display: flex;
    flex-direction: column;
  }

  .calendarConfigCard {
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

  .configIconWrapper {
    color: #e67e22;
    background: rgba(230, 126, 34, 0.1);
    width: 64px;
    height: 64px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    border: 1px solid rgba(230, 126, 34, 0.2);
    margin-bottom: 8px;
  }

  .calendarConfigCard h3 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 600;
  }

  .calendarConfigCard p {
    color: #aeb9c8;
    max-width: 480px;
    line-height: 1.5;
    margin: 0;
    font-size: 0.9rem;
  }

  .configGuide {
    text-align: left;
    background: #080b10;
    border: 1px solid #1c232e;
    border-radius: 6px;
    padding: 16px;
    font-size: 0.85rem;
    width: 100%;
    max-width: 480px;
  }

  .configGuide strong {
    display: block;
    margin-bottom: 8px;
  }

  .configGuide ol {
    margin: 0;
    padding-left: 20px;
    display: grid;
    gap: 6px;
    color: #8b98aa;
  }

  .configGuide code {
    background: #182232;
    padding: 2px 6px;
    border-radius: 4px;
    color: #e67e22;
    font-family: Consolas, monospace;
    display: block;
    margin-top: 4px;
    overflow-x: auto;
  }

  .setupRetryButton {
    border: 1px solid #2b3544;
    border-radius: 8px;
    background: #141d29;
    color: #eef2f8;
    padding: 10px 20px;
    margin-top: 8px;
    font-weight: 500;
  }

  .setupRetryButton:hover {
    border-color: #4a8dd8;
    background: #1d4f86;
  }

  .agendaTimeline {
    display: grid;
    gap: 20px;
  }

  .agendaDayGroup {
    display: grid;
    gap: 8px;
  }

  .agendaDayHeader {
    margin: 0;
    font-size: 0.88rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #8b98aa;
    border-bottom: 1px solid #1c232e;
    padding-bottom: 6px;
  }

  .agendaDayItems {
    display: grid;
    gap: 8px;
  }

  .eventCard {
    display: flex;
    border: 1px solid #242c38;
    border-radius: 8px;
    background: #101722;
    overflow: hidden;
    transition: all 0.2s;
  }

  .eventCard:hover {
    border-color: #4a8dd8;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .eventTimeBar {
    width: 4px;
    background: linear-gradient(to bottom, #4a8dd8, #1d4f86);
    flex-shrink: 0;
  }

  .eventBody {
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .eventTime {
    font-size: 0.78rem;
    color: #8b98aa;
  }

  .eventSummary {
    font-size: 0.95rem;
    font-weight: 600;
    color: #eef2f8;
    overflow-wrap: anywhere;
  }

  .eventLocation {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.78rem;
    color: #8b98aa;
    margin-top: 2px;
  }

  .locationIcon {
    flex-shrink: 0;
    color: #e67e22;
  }
</style>
