<script>
  import { onMount, tick } from 'svelte'
  import Icons from './Icons.svelte'

  const API_BASE = import.meta.env.DEV ? 'http://127.0.0.1:5000' : ''

  let messages = $state([
    {
      sender: 'assistant',
      text: 'Hello! I am WallSync Agent. I can help coordinate your dashboard tasks, daily habits, and calendar details. How can I assist you today?'
    }
  ])
  let promptText = $state('')
  let isSending = $state(false)
  let chatLogRef = $state(null)

  async function scrollToBottom() {
    await tick()
    if (chatLogRef) {
      chatLogRef.scrollTop = chatLogRef.scrollHeight
    }
  }

  async function sendMessage() {
    const text = promptText.trim()
    if (!text || isSending) return

    messages = [...messages, { sender: 'user', text }]
    promptText = ''
    isSending = true
    await scrollToBottom()

    try {
      const response = await fetch(`${API_BASE}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      })

      if (!response.ok) throw new Error('Agent failed to reply')
      
      const payload = await response.json()
      messages = [...messages, { sender: 'assistant', text: payload.reply }]
    } catch (err) {
      messages = [...messages, { sender: 'assistant', text: `Error: ${err.message}` }]
    } finally {
      isSending = false
      await scrollToBottom()
    }
  }

  onMount(scrollToBottom)
</script>

<section class="panel aiPanel">
  <div class="sectionHeader">
    <h2>✦ WallSync Agent</h2>
    <span class="statusPill">Local Stub</span>
  </div>

  <div class="chatLog" bind:this={chatLogRef}>
    {#each messages as message}
      <article class="message {message.sender}">
        <div class="avatar">
          {#if message.sender === 'assistant'}
            <Icons name="agent" size={14} />
          {:else}
            U
          {/if}
        </div>
        <div class="messageBubble">
          <p>{message.text}</p>
        </div>
      </article>
    {/each}
    {#if isSending}
      <div class="message assistant typingIndicator">
        <div class="avatar">
          <Icons name="agent" size={14} class="spinning" />
        </div>
        <div class="messageBubble">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>
    {/if}
  </div>

  <form class="composer" onsubmit={(event) => { event.preventDefault(); sendMessage() }}>
    <input bind:value={promptText} type="text" placeholder="Ask WallSync..." aria-label="Chat input" disabled={isSending} />
    <button type="submit" disabled={isSending || !promptText.trim()}>
      Send
    </button>
  </form>
</section>

<style>
  .aiPanel {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .chatLog {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding-right: 4px;
    margin-bottom: 16px;
  }

  .message {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    border: none;
    background: none;
    padding: 0;
  }

  .message.user {
    flex-direction: row-reverse;
  }

  .avatar {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #141d29;
    border: 1px solid #2b3544;
    display: grid;
    place-items: center;
    font-size: 0.72rem;
    font-weight: 700;
    color: #8b98aa;
    flex-shrink: 0;
  }

  .message.assistant .avatar {
    color: #4a8dd8;
    background: rgba(74, 141, 216, 0.1);
    border-color: rgba(74, 141, 216, 0.2);
  }

  .messageBubble {
    max-width: 80%;
    background: #101722;
    border: 1px solid #242c38;
    border-radius: 12px;
    border-top-left-radius: 2px;
    padding: 10px 14px;
  }

  .message.user .messageBubble {
    background: #1d4f86;
    border-color: #4a8dd8;
    border-radius: 12px;
    border-top-right-radius: 2px;
  }

  .messageBubble p {
    margin: 0 !important;
    font-size: 0.88rem;
    color: #eef2f8 !important;
    line-height: 1.45;
  }

  .message.user .messageBubble p {
    color: #ffffff !important;
  }

  .typingIndicator .messageBubble {
    display: flex;
    gap: 4px;
    align-items: center;
    padding: 12px 16px;
  }

  .dot {
    width: 6px;
    height: 6px;
    background: #8b98aa;
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out both;
  }

  .dot:nth-child(1) { animation-delay: -0.32s; }
  .dot:nth-child(2) { animation-delay: -0.16s; }

  @keyframes bounce {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1.0); }
  }
</style>
