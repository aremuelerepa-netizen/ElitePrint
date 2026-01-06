async function sendMessage() {
    const input = document.getElementById('userInput');
    const chatBox = document.getElementById('chat-box');
    const text = input.value.trim();

    if (!text) return;

    // 1. Add User Message to screen
    chatBox.innerHTML += `<div class="msg user-msg">${text}</div>`;
    input.value = '';
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        // 2. Send to Render Backend (/chat)
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();
        
        // 3. Add Bot Response to screen
        chatBox.innerHTML += `<div class="msg bot-msg">${data.response}</div>`;
        chatBox.scrollTop = chatBox.scrollHeight;
    } catch (error) {
        chatBox.innerHTML += `<div class="msg bot-msg">Connection lost. Please refresh.</div>`;
    }
}