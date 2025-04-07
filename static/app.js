document.addEventListener("DOMContentLoaded", function () {
    const chatForm = document.getElementById("chat-form");
    const chatBox = document.getElementById("chat-box");
    const userInput = document.getElementById("user-input");
    const monthSelect = document.getElementById("months");

    chatForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const userMessage = userInput.value.trim();
        let selectedMonth = monthSelect.value;
        if (!userMessage) return;

        selectedMonth = parseInt(selectedMonth, 10);
        if (isNaN(selectedMonth)) {
            console.error("선택된 개월 수가 유효한 숫자가 아닙니다.");
            return;
        }

        // 사용자 메시지 출력
        const userMsgElement = document.createElement("div");
        userMsgElement.classList.add("message", "user");
        userMsgElement.textContent = `[${selectedMonth}개월] ${userMessage}`;
        chatBox.appendChild(userMsgElement);

        userInput.value = "";

        // 스트리밍 응답 요청
        const response = await fetch("/chat/stream/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                prompt: userMessage,
                months: selectedMonth
            }),
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
            const chunk = decoder.decode(value);
            botMsgElement.textContent += chunk;
            chatBox.scrollTop = chatBox.scrollHeight; // 자동 스크롤
        }
    });
});