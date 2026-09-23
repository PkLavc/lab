(() => {
  const apiBase = 'https://api.pklavc.com';
  const form = document.querySelector('#speech-form');
  const input = document.querySelector('#speech-input');
  const log = document.querySelector('#chat-log');
  const voiceButton = document.querySelector('#voice-toggle');
  const viewport = document.querySelector('#viewport');
  let conversationId = null;
  let voiceOutput = false;
  let characterSpeech = false;

  const escapeHtml = value => value.replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));

  function appendMessage(role, text, pending = false) {
    const article = document.createElement('article');
    article.className = `lab-chat-message lab-chat-message--${role}${pending ? ' is-pending' : ''}`;
    article.innerHTML = `<div class="lab-chat-bubble">${escapeHtml(text).replace(/\n/g, '<br>')}</div>`;
    log.append(article);
    log.scrollTop = log.scrollHeight;
    return article;
  }

  function autoResize() {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 132)}px`;
  }

  function speakThroughOriginalController(text) {
    const previousValue = input.value;
    characterSpeech = true;
    input.value = text;
    try { form.requestSubmit(); }
    finally {
      input.value = previousValue;
      characterSpeech = false;
      autoResize();
    }
  }

  async function send() {
    const message = input.value.trim();
    if (!message) return;
    input.value = '';
    autoResize();
    appendMessage('user', message);
    if (message === '1997') {
      viewport.classList.add('is-s800-revealed');
      input.focus();
      return;
    }

    const waiting = appendMessage('assistant', '...', true);
    try {
      const response = await fetch(`${apiBase}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, conversation_id: conversationId, voice_reply: voiceOutput })
      });
      const contentType = response.headers.get('content-type') || '';
      const data = contentType.includes('application/json') ? await response.json() : {};
      if (!response.ok) throw new Error(data.error || `chat_http_${response.status}`);
      conversationId = data.conversation_id || conversationId;
      const reply = data.reply || 'Não consegui responder agora. Tente novamente.';
      waiting.classList.remove('is-pending');
      waiting.querySelector('.lab-chat-bubble').innerHTML = escapeHtml(reply).replace(/\n/g, '<br>');
      if (voiceOutput) speakThroughOriginalController(reply);
    } catch (error) {
      waiting.classList.remove('is-pending');
      waiting.querySelector('.lab-chat-bubble').textContent = 'Não consegui responder agora. Tente novamente.';
      console.error('Skylet Lab chat request failed:', error);
    }
    log.scrollTop = log.scrollHeight;
    input.focus();
  }

  form.addEventListener('submit', event => {
    if (characterSpeech) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    send();
  }, true);
  input.addEventListener('input', autoResize);
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  voiceButton.addEventListener('click', () => {
    voiceOutput = !voiceOutput;
    voiceButton.classList.toggle('is-active', voiceOutput);
    voiceButton.setAttribute('aria-pressed', String(voiceOutput));
    const label = voiceOutput ? 'Respostas em áudio ligadas' : 'Respostas em áudio desligadas';
    voiceButton.setAttribute('aria-label', label);
    voiceButton.setAttribute('title', label);
  });
  document.querySelectorAll('[data-current-year]').forEach(node => { node.textContent = String(new Date().getFullYear()); });
  autoResize();
  input.focus();
})();
