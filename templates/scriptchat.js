 // Dark mode toggling
 function toggleDarkMode() {
    const html = document.documentElement;
    html.classList.toggle('dark');
    const isDark = html.classList.contains('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  }

  // On page load, load local settings
  document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.classList.toggle('dark', savedTheme === 'dark');

    const sidebarState = localStorage.getItem('sidebarState');
    if (sidebarState === 'partiallyHidden') {
      document.documentElement.classList.add('sidebar-partially-hidden');
    }
  });

  // Toggle partial hidden sidebar
  function toggleSidebar() {
    document.documentElement.classList.toggle('sidebar-partially-hidden');
    const isHidden = document.documentElement.classList.contains('sidebar-partially-hidden');
    localStorage.setItem('sidebarState', isHidden ? 'partiallyHidden' : 'visible');
  }

  let chat_id = null;

  function appendMessage(content, classes) {
    const chatWindow = document.getElementById('chatWindow');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message-bubble ${classes}`;
    messageDiv.textContent = content;
    chatWindow.appendChild(messageDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  async function selectChat(id) {
    chat_id = id;
    document.getElementById('hiddenChatId').value = id;
    const chatWindow = document.getElementById('chatWindow');
    chatWindow.innerHTML = '';

    try {
      const response = await fetch(`/developerassistant/chat/${id}`);
      if (response.ok) {
        const data = await response.json();
        data.chat_details.forEach(([prompt, resp]) => {
          appendMessage(prompt, "message-outgoing");
          appendMessage(resp, "message-incoming");
        });
      } else {
        appendMessage('Failed to fetch chat history.', "message-error");
      }
    } catch (error) {
      appendMessage('Error fetching the chat.', "message-error");
    }
  }

  async function createNewChat() {
    try {
      const response = await fetch('/developerassistant/new_chat', {
        method: 'POST'
      });
      if (response.ok) {
        const data = await response.json();
        const newChat = document.createElement('li');
        newChat.className = "sidebar-item";
        newChat.innerText = data.chat_name;
        newChat.onclick = () => selectChat(data.chat_id);
        document.getElementById('sidebarList').prepend(newChat);
        selectChat(data.chat_id);
      } else {
        appendMessage('Error creating new chat.', "message-error");
      }
    } catch (error) {
      appendMessage('Server error creating new chat.', "message-error");
    }
  }

  async function sendMessage(event) {
    event.preventDefault();
    const textArea = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const message = textArea.value.trim();

    if (!message) return;

    const formData = new FormData();
    formData.append('chat_id', chat_id || '');
    formData.append('userInput', message);

    appendMessage(message, "message-outgoing");
    textArea.value = '';
    sendButton.disabled = true;

    try {
      const response = await fetch('/developerassistant/', {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        if (data.error) {
          appendMessage(data.error, "message-error");
        } else {
          appendMessage(data.response, "message-incoming");
          if (data.chat_id) {
            chat_id = data.chat_id;
            document.getElementById('hiddenChatId').value = data.chat_id;
          }
        }
      } else {
        appendMessage('Server error submitting data.', "message-error");
      }
    } catch (error) {
      appendMessage('Error connecting to the server.', "message-error");
    } finally {
      sendButton.disabled = false;
    }
  }