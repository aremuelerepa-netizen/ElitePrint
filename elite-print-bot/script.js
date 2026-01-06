// Function to scroll chat to the bottom
function scrollToBottom() {
    const chatBox = document.getElementById('chat-box');
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Load history from the phone's memory when page opens
window.onload = () => {
    const savedChat = localStorage.getItem('eliteChatHistory');
    if (savedChat) {
        document.getElementById('chat-box').innerHTML = savedChat;
        scrollToBottom();
    }
};

// Sidebar Toggle
function toggleMenu() {
    document.getElementById('sidebar').classList.toggle('active');
    document.getElementById('overlay').classList.toggle('active');
}

// Quick Button Click
function sendQuickMsg(text) {
    document.getElementById('userInput').value = text;
    sendMessage();
}

// Clear History
function clearChat() {
    if(confirm("Start a new chat?")) {
        localStorage.removeItem('eliteChatHistory');
        location.reload();
    }
}

// MAIN FUNCTION: TALK TO LLAMA
async function sendMessage() {
    const input = document.getElementById('userInput');
    const chatBox = document.getElementById('chat-box');
    const userText = input.value.trim();

    if (!userText) return;

    // 1. Show User Text
    chatBox.innerHTML += `<div class="msg user-msg">${userText}</div>`;
    input.value = '';
    scrollToBottom();

    // 2. Show "Typing..." Bubble
    const loadingId = "load-" + Date.now();
    chatBox.innerHTML += `<div class="msg bot-msg" id="${loadingId}">Elite AI is typing...</div>`;
    scrollToBottom();

    try {
        // 3. Connect to your Render backend
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userText })
        });

        const data = await response.json();
        
        // 4. Update with real Llama reply
        document.getElementById(loadingId).innerText = data.response;
        
        // 5. Save history
        localStorage.setItem('eliteChatHistory', chatBox.innerHTML);

    } catch (error) {
        document.getElementById(loadingId).innerText = "Connection lost. Please check your internet.";
    }
    scrollToBottom();
}

// Allow "Enter" key to send
document.getElementById('userInput').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});
