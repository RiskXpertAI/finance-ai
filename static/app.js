document.addEventListener("DOMContentLoaded", function () {
    const chatForm = document.getElementById("chat-form");
    const chatBox = document.getElementById("chat-box");
    const userInput = document.getElementById("user-input");
    const monthSelect = document.getElementById("months"); // ✅ 개월 수 선택

    chatForm.addEventListener("submit", async function (event) {
        event.preventDefault(); // 기본 제출 방지

        const userMessage = userInput.value.trim();
        const selectedMonth = monthSelect.value; // ✅ 선택된 개월 수 가져오기
        if (!userMessage) return;

        // ✅ 사용자 메시지 추가
        const userMsgElement = document.createElement("div");
        userMsgElement.classList.add("message", "user");
        userMsgElement.textContent = `[${selectedMonth}개월] ${userMessage}`;
        chatBox.appendChild(userMsgElement);

        // 입력창 초기화
        userInput.value = "";

        // ✅ 서버에 메시지 전송
        const response = await fetch("/chat/", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ prompt: userMessage }),
        });

        if (response.ok) {
            const botMessage = await response.text();

            // ✅ 챗봇 메시지 추가
            const botMsgElement = document.createElement("div");
            botMsgElement.classList.add("message", "bot");
            botMsgElement.innerHTML = botMessage;
            chatBox.appendChild(botMsgElement);

            // 자동 스크롤
            chatBox.scrollTop = chatBox.scrollHeight;
        } else {
            console.error("챗봇 응답 오류");
        }
    });
});
