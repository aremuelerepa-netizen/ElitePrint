// 1. SCROLL TO BOTTOM
function scrollToBottom() {
    const chatBox = document.getElementById('chat-box');
    if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

// 2. LOAD HISTORY
window.onload = () => {
    const chatBox = document.getElementById('chat-box');
    const savedChat = localStorage.getItem('eliteChatHistory');
    if (savedChat && chatBox) {
        chatBox.innerHTML = savedChat;
        scrollToBottom();
    }
};

// 3. MENU TOGGLE
function toggleMenu() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    if (sidebar && overlay) {
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
    }
}

// 4. QUICK MESSAGES
function sendQuickMsg(text) {
    const input = document.getElementById('userInput');
    if (input) {
        input.value = text;
        sendMessage();
    }
}

// 5. CLEAR HISTORY
function clearChat() {
    if(confirm("Start a new chat?")) {
        localStorage.removeItem('eliteChatHistory');
        location.reload();
    }
}

// 6. MAIN SEND FUNCTION (TALK TO LLAMA)
async function sendMessage() {
    const input = document.getElementById('userInput');
    const chatBox = document.getElementById('chat-box');
    
    if (!input || !chatBox) return;

    const userText = input.value.trim();
    if (!userText) return;

    // Show User Text
    chatBox.innerHTML += `<div class="msg user-msg">${userText}</div>`;
    input.value = '';
    scrollToBottom();

    // Show "Typing..." Bubble
    const loadingId = "load-" + Date.now();
    chatBox.innerHTML += `<div class="msg bot-msg" id="${loadingId}">Elite AI is typing...</div>`;
    scrollToBottom();

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userText })
        });

        const data = await response.json();
        
        const botBubble = document.getElementById(loadingId);
        if (botBubble) {
            botBubble.innerText = data.response;
        }
        
        // Save history to device
        localStorage.setItem('eliteChatHistory', chatBox.innerHTML);

    } catch (error) {
        const botBubble = document.getElementById(loadingId);
        if (botBubble) {
            botBubble.innerText = "Connection weak. Please check your data.";
        }
    }
    scrollToBottom();
}

// 7. KEYBOARD LISTENER (ENTER KEY)
// Wrapped in DOMContentLoaded so it doesn't break buttons on load
document.addEventListener('DOMContentLoaded', () => {
    const userInput = document.getElementById('userInput');
    if (userInput) {
        userInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
});
