// 토큰 처리
window.onload = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const newAccess = urlParams.get("access_token");
    const newRefresh = urlParams.get("refresh_token");

    if (newAccess && newRefresh) {
        localStorage.setItem("access_token", newAccess);
        localStorage.setItem("refresh_token", newRefresh);
        window.history.replaceState({}, document.title, "/main");
    }

    const access = localStorage.getItem("access_token");
    const refresh = localStorage.getItem("refresh_token");

    if (!access || !refresh) {
        window.location.href = "/";
    }

    const logoutBtn = document.getElementById("logout-button");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", function () {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            window.location.href = "/";
        });
    }
};

// 채팅 처리
document.addEventListener("DOMContentLoaded", function () {
    const chatForm = document.getElementById("chat-form");
    const chatBox = document.getElementById("chat-box");
    const userInput = document.getElementById("user-input");
    const monthSelect = document.getElementById("months");

    chatForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const userMessage = userInput.value.trim();
        const selectedMonth = parseInt(monthSelect.value, 10);
        if (!userMessage || isNaN(selectedMonth)) return;

        const userMsgElement = document.createElement("div");
        userMsgElement.classList.add("message", "user");
        userMsgElement.textContent = `[${selectedMonth}개월] ${userMessage}`;
        chatBox.appendChild(userMsgElement);

        userInput.value = "";

        const response = await fetch("/chat/stream/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: userMessage, months: selectedMonth }),
        });

        if (!response.ok || !response.body) {
            console.error("스트리밍 응답 오류");
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        const botMsgElement = document.createElement("div");
        botMsgElement.classList.add("message", "bot");
        botMsgElement.textContent = "";
        chatBox.appendChild(botMsgElement);

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            botMsgElement.textContent += decoder.decode(value);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    });
});