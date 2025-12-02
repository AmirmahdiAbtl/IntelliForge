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
 // Extract RAG ID from URL like /rag/4/chat-interface
 const urlParts = window.location.pathname.split('/');
 const ragIndex = urlParts.indexOf('rag');
 if (ragIndex !== -1 && ragIndex + 1 < urlParts.length) {
   rag_id = urlParts[ragIndex + 1];
 }
 // Also get from hidden field if available
 const hiddenRagId = document.getElementById('hiddenRagId');
 if (hiddenRagId && hiddenRagId.value) {
   rag_id = hiddenRagId.value;
 }
 if (hiddenRagId) {
   hiddenRagId.value = rag_id;
 }
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
   
   const thinkingContent = document.createElement('div');
   thinkingContent.className = 'thinking-content';
   
   // Extract content between think tags and parse markdown
   const thinkingMatch = content.match(/<think>([\s\S]*?)<\/think>/);
   if (thinkingMatch) {
     thinkingContent.innerHTML = marked.parse(thinkingMatch[1]);
   }
   
   thinkingDiv.appendChild(header);
   thinkingDiv.appendChild(thinkingContent);
   
   // Add click handler for toggle
   header.addEventListener('click', () => {
     thinkingContent.classList.toggle('show');
     header.querySelector('.thinking-toggle').classList.toggle('rotated');
   });
   
   contentWrapper.appendChild(thinkingDiv);
   
   // Remove the thinking content from the main message
   content = content.replace(/<think>[\s\S]*?<\/think>/, '');
 }

 // Check if content contains sources
 if (content.includes('<sources>') && content.includes('</sources>')) {
   const sourcesDiv = document.createElement('div');
   sourcesDiv.className = 'sources-dropdown';
   
   const header = document.createElement('div');
   header.className = 'sources-header';
   header.innerHTML = `
     <span><i class="fas fa-book"></i> Sources</span>
     <span class="sources-toggle">▼</span>
   `;
   
   const sourcesContent = document.createElement('div');
   sourcesContent.className = 'sources-content';
   
   // Extract sources from tags
   const sourcesMatch = content.match(/<sources>([\s\S]*?)<\/sources>/);
   if (sourcesMatch) {
     try {
       const sources = JSON.parse(sourcesMatch[1]);
       const sourcesList = document.createElement('ul');
       sourcesList.className = 'sources-list';
       
       sources.forEach((source, index) => {
         const listItem = document.createElement('li');
         listItem.innerHTML = `<strong>Source ${index + 1}:</strong> ${source.substring(0, 200)}${source.length > 200 ? '...' : ''}`;
         sourcesList.appendChild(listItem);
       });
       
       sourcesContent.appendChild(sourcesList);
     } catch (e) {
       sourcesContent.innerHTML = '<p>Error loading sources</p>';
     }
   }
   
   sourcesDiv.appendChild(header);
   sourcesDiv.appendChild(sourcesContent);
   
   // Add click handler for toggle
   header.addEventListener('click', () => {
     sourcesContent.classList.toggle('show');
     header.querySelector('.sources-toggle').classList.toggle('rotated');
   });
   
   contentWrapper.appendChild(sourcesDiv);
   
   // Remove the sources content from the main message
   content = content.replace(/<sources>[\s\S]*?<\/sources>/, '');
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


async function selectSession(sessionId) {
 chat_id = sessionId;
 document.getElementById('hiddenChatId').value = sessionId;
 const chatWindow = document.getElementById('chatWindow');
 chatWindow.innerHTML = '';

 try {
   const ragId = document.getElementById('hiddenRagId').value;
   const response = await fetch(`/rag/${ragId}/session/${sessionId}/history`);
   if (response.ok) {
     const data = await response.json();
     if (data.error) {
       appendMessage(data.error, "message-error");
     } else {
       data.forEach(msg => {
         appendMessage(msg.user_message, "message-outgoing");
         appendMessage(msg.bot_response, "message-incoming");
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

   // Prepare data for new session
   
   const response = await fetch(`/rag/${ragId}/new-session`, {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json'
     },
     body: JSON.stringify({
       session_name: 'New Session'
     })
   });
   
   if (response.ok) {
     const data = await response.json();
     if (data.error) {
       appendMessage(data.error, "message-error");
     } else {
       const newChat = document.createElement('li');
       newChat.className = "sidebar-item";
       newChat.innerText = data.session_name;
       newChat.onclick = () => selectSession(data.session_id);
       document.getElementById('sidebarList').prepend(newChat);
       selectSession(data.session_id);
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
    formData.append('session_id', chat_id || '');
    formData.append('userInput', message);
    formData.append('rag_id', rag_id);

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
        const response = await fetch(`/rag/${rag_id}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                rag_id: parseInt(rag_id),
                query: message,
                session_id: chat_id
            })
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
                // Update session ID if provided
                if (data.session_id) {
                    chat_id = data.session_id;
                    document.getElementById('hiddenChatId').value = data.session_id;
                }
                
                // Create message content with sources dropdown
                let messageContent = data.answer;
                if (data.sources && data.sources.length > 0) {
                    messageContent += '\n\n<sources>' + JSON.stringify(data.sources) + '</sources>';
                }
                appendMessage(messageContent, "message-incoming");
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