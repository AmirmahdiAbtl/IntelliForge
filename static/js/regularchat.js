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

 // Groq temperature
 const groqTemp = document.getElementById('groqTemperature');
 const groqTempValue = document.getElementById('groqTemperatureValue');
 groqTemp.addEventListener('input', function() {
   groqTempValue.textContent = this.value;
 });

 // Ollama temperature
 const ollamaTemp = document.getElementById('ollamaTemperature');
 const ollamaTempValue = document.getElementById('ollamaTemperatureValue');
 ollamaTemp.addEventListener('input', function() {
   ollamaTempValue.textContent = this.value;
 });

 // GPT temperature
 const gptTemp = document.getElementById('gptTemperature');
 const gptTempValue = document.getElementById('gptTemperatureValue');
 gptTemp.addEventListener('input', function() {
   gptTempValue.textContent = this.value;
 });

 // Load saved configuration
 loadConfig();
});

// Toggle partial hidden sidebar
function toggleSidebar() {
 document.documentElement.classList.toggle('sidebar-partially-hidden');
 const isHidden = document.documentElement.classList.contains('sidebar-partially-hidden');
 localStorage.setItem('sidebarState', isHidden ? 'partiallyHidden' : 'visible');
}

let chat_id = null;
//  let rag_id = null; // set this dynamically as needed

// Example: set rag_id when the page loads or from the URL
document.addEventListener("DOMContentLoaded", () => {
 // Example: extract from URL if needed
//    const urlParts = window.location.pathname.split('/');
//    rag_id = urlParts[urlParts.length - 1]; // if URL is like .../chat/123
//    document.getElementById('hiddenRagId').value = rag_id;
});

// Replace your appendMessage function with this:
function appendMessage(content, classes) {
 const chatWindow = document.getElementById('chatWindow');
 const messageDiv = document.createElement('div');
 messageDiv.className = `message-bubble ${classes}`;

 const contentWrapper = document.createElement('div'); // Wraps the message content

 // Check if content contains thinking part
 if (content.includes('<think>') && content.includes('</think>')) {
   // Extract thinking and response parts
   const thinkingMatch = content.match(/<think>([\s\S]*?)<\/think>/);
   const thinkingContent = thinkingMatch ? thinkingMatch[1].trim() : '';
   const responseContent = content.replace(/<think>[\s\S]*?<\/think>/, '').trim();

   // Create thinking dropdown
   const thinkingDropdown = document.createElement('div');
   thinkingDropdown.className = 'thinking-dropdown';

   const thinkingHeader = document.createElement('div');
   thinkingHeader.className = 'thinking-header';
   thinkingHeader.innerHTML = `
     <span>Thinking Process</span>
     <i class="fas fa-chevron-down thinking-toggle"></i>
   `;

   const thinkingContentDiv = document.createElement('div');
   thinkingContentDiv.className = 'thinking-content';
   thinkingContentDiv.innerHTML = marked.parse(thinkingContent);

   thinkingDropdown.appendChild(thinkingHeader);
   thinkingDropdown.appendChild(thinkingContentDiv);
   contentWrapper.appendChild(thinkingDropdown);

   // Add click handler for toggle
   thinkingHeader.addEventListener('click', () => {
     thinkingContentDiv.classList.toggle('show');
     const toggle = thinkingHeader.querySelector('.thinking-toggle');
     toggle.classList.toggle('rotated');
   });

   // Add response content
   const responseDiv = document.createElement('div');
   responseDiv.className = 'markdown-text';
   responseDiv.innerHTML = marked.parse(responseContent);
   contentWrapper.appendChild(responseDiv);
 } else {
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
 }

 messageDiv.appendChild(contentWrapper);

 // ✅ Add full message copy button here
 const fullCopyBtn = document.createElement('button');
 fullCopyBtn.className = 'copy-full-btn';
 fullCopyBtn.innerHTML = '<i class="fas fa-copy"></i>';

 fullCopyBtn.addEventListener('click', () => {
   const tempDiv = contentWrapper.cloneNode(true);
   tempDiv.querySelectorAll('.copy-full-btn, .copy-btn').forEach(btn => btn.remove());
   const textToCopy = tempDiv.innerText;

   navigator.clipboard.writeText(textToCopy).then(() => {
     fullCopyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
     setTimeout(() => {
       fullCopyBtn.innerHTML = '<i class="fas fa-copy"></i>';
     }, 2000);
   });
 });

 messageDiv.appendChild(fullCopyBtn); // Add the button outside the content wrapper
 chatWindow.appendChild(messageDiv);
 chatWindow.scrollTop = chatWindow.scrollHeight;
}


async function selectChat(id) {
 chat_id = id;
 document.getElementById('hiddenChatId').value = id;
 const chatWindow = document.getElementById('chatWindow');
 chatWindow.innerHTML = '';

 try {
   const response = await fetch(`/regularchat/${id}`);
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

// Add this new function to check configuration
async function checkConfiguration(chatId) {
    try {
        const response = await fetch(`/regularchat/get_model_config?chat_id=${chatId}`);
        if (response.ok) {
            const config = await response.json();
            return config && config.language_model !== 'pending' && config.api_key !== 'pending';
        }
        return false;
    } catch (error) {
        console.error('Error checking configuration:', error);
        return false;
    }
}

async function sendMessage(event) {
    event.preventDefault();
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const message = userInput.value.trim();
    const chatId = document.getElementById('hiddenChatId').value;

    if (!message) return;

    // Check configuration before sending
    const isConfigured = await checkConfiguration(chatId);
    if (!isConfigured) {
        appendMessage("Please configure the chat model before sending messages. Click the gear icon to configure.", "message-error");
        toggleConfigModal();
        return;
    }

    // Disable input and button while sending
    userInput.disabled = true;
    sendButton.disabled = true;
    sendButton.style.opacity = '0.5';
    userInput.style.opacity = '0.5';

    // Clear input and reset height
    userInput.value = '';
    userInput.style.height = 'auto';

    // Add user message to chat
    appendMessage(message, "message-outgoing");

    // Add "Answering..." message
    const answeringDiv = document.createElement('div');
    answeringDiv.className = 'message-bubble message-incoming';
    answeringDiv.id = 'answering-message';
    answeringDiv.textContent = 'Answering...';
    document.getElementById('chatWindow').appendChild(answeringDiv);
    document.getElementById('chatWindow').scrollTop = document.getElementById('chatWindow').scrollHeight;

    try {
        const formData = new FormData();
        formData.append('userInput', message);
        formData.append('chat_id', chatId);

        const response = await fetch('/regularchat/', {
            method: 'POST',
            body: formData
        });

        // Remove "Answering..." message
        const answeringMessage = document.getElementById('answering-message');
        if (answeringMessage) {
            answeringMessage.remove();
        }

        const data = await response.json();
        
        if (response.ok) {
            appendMessage(data.response, "message-incoming");
        } else {
            appendMessage(data.error || 'Error sending message', "message-error");
        }
    } catch (error) {
        // Remove "Answering..." message
        const answeringMessage = document.getElementById('answering-message');
        if (answeringMessage) {
            answeringMessage.remove();
        }
        appendMessage('Server error sending message', "message-error");
    } finally {
        // Re-enable input and button
        userInput.disabled = false;
        sendButton.disabled = false;
        sendButton.style.opacity = '1';
        userInput.style.opacity = '1';
        userInput.focus(); // Focus back on input
    }
}

async function createNewChat() {
    try {
        const formData = new FormData();
        
        const response = await fetch('/regularchat/new_chat', {
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
                
                // Update the hidden chat ID
                document.getElementById('hiddenChatId').value = data.chat_id;
                
                // Show configuration message and modal
                appendMessage("Please configure the chat model before sending messages. Click the gear icon to configure.", "message-error");
                toggleConfigModal();
                
                // Select the new chat
                selectChat(data.chat_id);
            }
        } else {
            appendMessage('Error creating new chat.', "message-error");
        }
    } catch (error) {
        appendMessage('Server error creating new chat.', "message-error");
    }
}

// Configuration Modal Functions
function toggleConfigModal() {
    const modal = document.getElementById('configModal');
    modal.style.display = modal.style.display === 'block' ? 'none' : 'block';
    
    if (modal.style.display === 'block') {
        loadCurrentConfig();
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('configModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Tab functionality
function openTab(evt, tabName) {
    // Hide all tab content
    const tabContents = document.getElementsByClassName('tab-content');
    for (let i = 0; i < tabContents.length; i++) {
        tabContents[i].classList.remove('active');
    }

    // Remove active class from all tab buttons
    const tabButtons = document.getElementsByClassName('tab-btn');
    for (let i = 0; i < tabButtons.length; i++) {
        tabButtons[i].classList.remove('active');
    }

    // Show the current tab and add active class to the button
    document.getElementById(tabName).classList.add('active');
    evt.currentTarget.classList.add('active');
}

// Load Ollama models
async function loadOllamaModels() {
    try {
        const response = await fetch('/ollama/models');
        if (response.ok) {
            const models = await response.json();
            const select = document.getElementById('ollamaModel');
            select.innerHTML = ''; // Clear loading message
            
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                select.appendChild(option);
            });
        } else {
            console.error('Failed to load Ollama models');
        }
    } catch (error) {
        console.error('Error loading Ollama models:', error);
    }
}

// Update saveConfig to refresh the chat after saving
async function saveConfig() {
    const activeTab = document.querySelector('.tab-btn.active').textContent.toLowerCase();
    let config = {
        provider: activeTab,
        language_model: '',
        model_type: '',
        api_key: '',
        temperature: 0.7,
        chat_id: document.getElementById('hiddenChatId').value
    };

    // Set configuration based on active tab
    switch(activeTab) {
        case 'groq':
            config.language_model = document.getElementById('groqModel').value;
            config.model_type = 'GROQ';
            config.api_key = document.getElementById('groqApiKey').value;
            config.temperature = parseFloat(document.getElementById('groqTemperature').value);
            break;
        case 'ollama':
            config.language_model = document.getElementById('ollamaModel').value;
            config.model_type = 'Ollama';
            config.api_key = ''; // Ollama doesn't need an API key
            config.temperature = parseFloat(document.getElementById('ollamaTemperature').value);
            break;
        case 'gpt':
            config.language_model = document.getElementById('gptModel').value;
            config.model_type = 'ChatGPT';
            config.api_key = document.getElementById('gptApiKey').value;
            config.temperature = parseFloat(document.getElementById('gptTemperature').value);
            break;
    }

    try {
        const response = await fetch('/regularchat/update_model_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            const data = await response.json();
            
            // If this was a new chat creation, update the UI
            if (data.chat_id && !config.chat_id) {
                document.getElementById('hiddenChatId').value = data.chat_id;
                
                // Add the new chat to the sidebar
                const sidebarList = document.getElementById('sidebarList');
                const newChat = document.createElement('li');
                newChat.className = 'sidebar-item';
                newChat.textContent = data.chat_name;
                newChat.onclick = () => selectChat(data.chat_id);
                sidebarList.prepend(newChat);
            }
            
            // Save to localStorage as backup
            localStorage.setItem('modelConfig', JSON.stringify(config));
            
            // Close modal
            toggleConfigModal();
            
            // Show success message
            appendMessage("Chat configured successfully! You can now send messages.", "message-success");
            
            // Refresh the chat to ensure we have the latest configuration
            if (config.chat_id) {
                selectChat(config.chat_id);
            }
        } else {
            const errorData = await response.json();
            appendMessage('Error saving configuration: ' + (errorData.error || 'Unknown error'), "message-error");
        }
    } catch (error) {
        console.error('Error:', error);
        appendMessage('Failed to save configuration. Please try again.', "message-error");
    }
}

// Load saved configuration
function loadConfig() {
    const savedConfig = localStorage.getItem('modelConfig');
    if (savedConfig) {
        const config = JSON.parse(savedConfig);
        
        // Set Groq config
        document.getElementById('groqApiKey').value = config.groq.apiKey || '';
        document.getElementById('groqModel').value = config.groq.model || '';
        document.getElementById('groqTemperature').value = config.groq.temperature || '0.7';
        document.getElementById('groqTemperatureValue').textContent = config.groq.temperature || '0.7';
        
        // Set Ollama config
        document.getElementById('ollamaModel').value = config.ollama.model || '';
        document.getElementById('ollamaTemperature').value = config.ollama.temperature || '0.7';
        document.getElementById('ollamaTemperatureValue').textContent = config.ollama.temperature || '0.7';
        
        // Set GPT config
        document.getElementById('gptApiKey').value = config.gpt.apiKey || '';
        document.getElementById('gptModel').value = config.gpt.model || 'gpt-3.5-turbo';
        document.getElementById('gptTemperature').value = config.gpt.temperature || '0.7';
        document.getElementById('gptTemperatureValue').textContent = config.gpt.temperature || '0.7';
        
        // Activate the saved provider's tab
        const tabButtons = document.getElementsByClassName('tab-btn');
        for (let i = 0; i < tabButtons.length; i++) {
            if (tabButtons[i].textContent.toLowerCase() === config.provider) {
                tabButtons[i].click();
                break;
            }
        }
    }
}

// Load current configuration from server
async function loadCurrentConfig() {
    try {
        const chat_id = document.getElementById('hiddenChatId').value;
        const response = await fetch(`/regularchat/get_model_config?chat_id=${chat_id}`);
        if (response.ok) {
            const config = await response.json();
            if (config) {
                // Set the active tab based on model_type
                const tabButtons = document.getElementsByClassName('tab-btn');
                for (let i = 0; i < tabButtons.length; i++) {
                    if (tabButtons[i].textContent.toLowerCase() === config.model_type.toLowerCase()) {
                        tabButtons[i].click();
                        break;
                    }
                }

                // Set the values based on the model type
                switch(config.model_type) {
                    case 'GROQ':
                        document.getElementById('groqModel').value = config.language_model || '';
                        document.getElementById('groqApiKey').value = config.api_key || '';
                        break;
                    case 'Ollama':
                        document.getElementById('ollamaModel').value = config.language_model || '';
                        break;
                    case 'ChatGPT':
                        document.getElementById('gptModel').value = config.language_model || 'gpt-3.5-turbo';
                        document.getElementById('gptApiKey').value = config.api_key || '';
                        break;
                }
            }
        }
    } catch (error) {
        console.error('Error loading configuration:', error);
    }
}

