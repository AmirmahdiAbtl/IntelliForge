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

 const userInput = document.getElementById("userInput");
  userInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      if (e.shiftKey) {
        return; // Insert newline
      } else {
        e.preventDefault(); // Prevent newline
        document.querySelector("form").requestSubmit(); // Submit the form
      }
    }
  });
});

// Toggle partial hidden sidebar
function toggleSidebar() {
 document.documentElement.classList.toggle('sidebar-partially-hidden');
 const isHidden = document.documentElement.classList.contains('sidebar-partially-hidden');
 localStorage.setItem('sidebarState', isHidden ? 'partiallyHidden' : 'visible');
}

let chat_id = null;
let rag_id = null; // set this dynamically as needed

// Example: set rag_id when the page loads or from the URL
document.addEventListener("DOMContentLoaded", () => {
 // Example: extract from URL if needed
 const urlParts = window.location.pathname.split('/');
 rag_id = urlParts[urlParts.length - 1]; // if URL is like .../chat/123
 document.getElementById('hiddenRagId').value = rag_id;
});

// Replace your appendMessage function with this:
function appendMessage(content, classes) {
 const chatWindow = document.getElementById('chatWindow');
 const messageDiv = document.createElement('div');
 messageDiv.className = `message-bubble ${classes}`;

 const contentWrapper = document.createElement('div'); // Wraps the message content

 // Check if content contains thinking tags
 if (content.includes('<think>') && content.includes('</think>')) {
   const thinkingDiv = document.createElement('div');
   thinkingDiv.className = 'thinking-dropdown';
   
   const header = document.createElement('div');
   header.className = 'thinking-header';
   header.innerHTML = `
     <span>Thinking Process</span>
     <span class="thinking-toggle">▼</span>
   `;
   
   const content = document.createElement('div');
   content.className = 'thinking-content';
   
   // Extract content between think tags and parse markdown
   const thinkingContent = content.match(/<think>([\s\S]*?)<\/think>/)[1];
   content.innerHTML = marked.parse(thinkingContent);
   
   thinkingDiv.appendChild(header);
   thinkingDiv.appendChild(content);
   
   // Add click handler for toggle
   header.addEventListener('click', () => {
     content.classList.toggle('show');
     header.querySelector('.thinking-toggle').classList.toggle('rotated');
   });
   
   contentWrapper.appendChild(thinkingDiv);
   
   // Remove the thinking content from the main message
   content = content.replace(/<think>[\s\S]*?<\/think>/, '');
 }

 // Parse content for code blocks
 const parts = content.split(/(```[\s\S]*?```)/g);
 parts.forEach(part => {
   if (part.startsWith('```') && part.endsWith('```')) {
     const codeContent = part.slice(3, -3).trim();
     const languageMatch = codeContent.match(/^(\w+)\n/);
     let language = 'text';
     let code = codeContent;

     if (languageMatch) {
       language = languageMatch[1];
       code = codeContent.slice(languageMatch[0].length);
     }

     const codeBlock = document.createElement('div');
     codeBlock.className = 'code-block';

     const codeHeader = document.createElement('div');
     codeHeader.className = 'code-header';
     codeHeader.innerHTML = `<span>${language}</span><button class="copy-btn">Copy</button>`;

     const codeElement = document.createElement('pre');
     codeElement.className = 'code-content';
     codeElement.textContent = code;

     codeBlock.appendChild(codeHeader);
     codeBlock.appendChild(codeElement);
     contentWrapper.appendChild(codeBlock);

     const copyBtn = codeHeader.querySelector('.copy-btn');
     copyBtn.addEventListener('click', () => {
       navigator.clipboard.writeText(code)
         .then(() => {
           copyBtn.textContent = 'Copied!';
           setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
         })
         .catch(err => console.error('Failed to copy text: ', err));
     });
   } else if (part.trim()) {
     const textNode = document.createElement('div');
     textNode.className = 'markdown-text';
     textNode.innerHTML = marked.parse(part);
     contentWrapper.appendChild(textNode);
   }
 });

 messageDiv.appendChild(contentWrapper);

 // Add full message copy button
 const fullCopyBtn = document.createElement('button');
 fullCopyBtn.className = 'copy-full-btn';
 fullCopyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy Message';

 fullCopyBtn.addEventListener('click', () => {
   const tempDiv = contentWrapper.cloneNode(true);
   tempDiv.querySelectorAll('.copy-full-btn, .copy-btn').forEach(btn => btn.remove());
   const textToCopy = tempDiv.innerText;

   navigator.clipboard.writeText(textToCopy).then(() => {
     fullCopyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
     setTimeout(() => {
       fullCopyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy Message';
     }, 2000);
   });
 });

 messageDiv.appendChild(fullCopyBtn);
 chatWindow.appendChild(messageDiv);
 chatWindow.scrollTop = chatWindow.scrollHeight;
}


async function selectChat(id) {
 chat_id = id;
 document.getElementById('hiddenChatId').value = id;
 const chatWindow = document.getElementById('chatWindow');
 chatWindow.innerHTML = '';

 try {
   const response = await fetch(`/developerassistant/chat_history/${id}`);
   if (response.ok) {
     const data = await response.json();
     if (data.error) {
       appendMessage(data.error, "message-error");
     } else {
       data.chat_details.forEach(([prompt, resp]) => {
         appendMessage(prompt, "message-outgoing");
         appendMessage(resp, "message-incoming");
       });
     }
   } else {
     appendMessage('Failed to fetch chat history.', "message-error");
   }
 } catch (error) {
   appendMessage('Error fetching the chat.', "message-error");
 }
}

async function createNewChat() {
 try {
   const ragId = document.getElementById('hiddenRagId').value;
   if (!ragId) {
     appendMessage('Error: No RAG ID provided', "message-error");
     return;
   }

   const formData = new FormData();
   formData.append('rag_id', ragId);
   
   const response = await fetch('/developerassistant/new_chat', {
     method: 'POST',
     body: formData
   });
   
   if (response.ok) {
     const data = await response.json();
     if (data.error) {
       appendMessage(data.error, "message-error");
     } else {
       const newChat = document.createElement('li');
       newChat.className = "sidebar-item";
       newChat.innerText = data.chat_name;
       newChat.onclick = () => selectChat(data.chat_id);
       document.getElementById('sidebarList').prepend(newChat);
       selectChat(data.chat_id);
     }
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
    rag_id = document.getElementById('hiddenRagId').value; // get current rag_id

    if (!message) return;

    // Disable input and button while sending
    textArea.disabled = true;
    sendButton.disabled = true;
    sendButton.style.opacity = '0.5';
    textArea.style.opacity = '0.5';

    const formData = new FormData();
    formData.append('chat_id', chat_id || '');
    formData.append('userInput', message);
    formData.append('rag_id', rag_id); // 🔥 send rag_id

    appendMessage(message, "message-outgoing");
    // Add "Answering..." message
    const answeringDiv = document.createElement('div');
    answeringDiv.className = 'message-bubble message-incoming';
    answeringDiv.id = 'answering-message';
    answeringDiv.textContent = 'Answering...';
    document.getElementById('chatWindow').appendChild(answeringDiv);
    document.getElementById('chatWindow').scrollTop = document.getElementById('chatWindow').scrollHeight;

    textArea.value = '';

    try {
        const response = await fetch('/developerassistant/', {
            method: 'POST',
            body: formData
        });

        // Remove "Answering..." message
        const answeringMessage = document.getElementById('answering-message');
        if (answeringMessage) {
            answeringMessage.remove();
        }

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
        // Remove "Answering..." message
        const answeringMessage = document.getElementById('answering-message');
        if (answeringMessage) {
            answeringMessage.remove();
        }
        appendMessage('Error connecting to the server.', "message-error");
    } finally {
        // Re-enable input and button
        textArea.disabled = false;
        sendButton.disabled = false;
        sendButton.style.opacity = '1';
        textArea.style.opacity = '1';
        textArea.focus(); // Focus back on input
    }
}
