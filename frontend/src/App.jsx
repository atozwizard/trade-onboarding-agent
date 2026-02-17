import { useEffect, useMemo, useRef, useState } from "react";
import ReportCard from "./components/ReportCard";
import { normalizeApiResponse, shouldForceQuizMode } from "./lib/normalizers";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
const SESSION_STORAGE_KEY = "trade_onboarding_session_id";

const MODE_OPTIONS = [
  { label: "자동 (Orchestrator 판단)", value: "auto" },
  { label: "리스크 분석 강제", value: "riskmanaging" },
  { label: "퀴즈 강제", value: "quiz" },
  { label: "이메일 강제", value: "email" },
  { label: "기본 대화 강제", value: "default_chat" },
];

function createSessionId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function QuizBlock({ questions, onSelectAnswer }) {
  return (
    <div className="quiz-block">
      {questions.map((question, index) => {
        const questionText = String(question.question || "질문 없음");
        const choices = Array.isArray(question.choices) ? question.choices : [];

        return (
          <div className="quiz-card" key={`${questionText}-${index}`}>
            <strong>[퀴즈 {index + 1}] {questionText}</strong>
            <ol>
              {choices.map((choice, choiceIndex) => (
                <li key={`${questionText}-${choiceIndex}`}>
                  <button
                    type="button"
                    className="choice-btn"
                    onClick={() => onSelectAnswer(String(choiceIndex + 1))}
                  >
                    {choiceIndex + 1}. {String(choice)}
                  </button>
                </li>
              ))}
            </ol>
          </div>
        );
      })}
      <p className="muted">번호를 직접 입력해도 됩니다. 예: `2` 또는 `2번`</p>
    </div>
  );
}

function AssistantContent({ message, onQuickAnswer }) {
  if (message.kind === "report") {
    return <ReportCard report={message.report} />;
  }

  if (message.kind === "quiz") {
    return <QuizBlock questions={message.questions || []} onSelectAnswer={onQuickAnswer} />;
  }

  if (message.kind === "email") {
    return (
      <div>
        <p>{message.text}</p>
        <pre>{JSON.stringify(message.data, null, 2)}</pre>
      </div>
    );
  }

  if (message.kind === "json") {
    return <pre>{JSON.stringify(message.data, null, 2)}</pre>;
  }

  if (message.kind === "error") {
    return (
      <div className="error-box">
        <strong>요청 처리 오류</strong>
        <p>{message.text}</p>
      </div>
    );
  }

  return <p className="multiline">{message.text}</p>;
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [mode, setMode] = useState("auto");
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    const cached = localStorage.getItem(SESSION_STORAGE_KEY);
    if (cached) {
      return cached;
    }
    const next = createSessionId();
    localStorage.setItem(SESSION_STORAGE_KEY, next);
    return next;
  });

  const listBottomRef = useRef(null);

  useEffect(() => {
    listBottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isSending]);

  const lastAssistantMessage = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "assistant") {
        return messages[i];
      }
    }
    return null;
  }, [messages]);

  const appendUserMessage = (text) => {
    const userMessage = {
      id: createSessionId(),
      role: "user",
      text,
    };
    setMessages((prev) => [...prev, userMessage]);
  };

  const appendAssistantMessage = (normalized) => {
    const assistantMessage = {
      id: createSessionId(),
      role: "assistant",
      ...normalized,
    };
    setMessages((prev) => [...prev, assistantMessage]);
  };

  const resetConversation = () => {
    const nextSession = createSessionId();
    localStorage.setItem(SESSION_STORAGE_KEY, nextSession);
    setSessionId(nextSession);
    setMessages([]);
    setInputValue("");
  };

  const sendMessage = async (rawText) => {
    const text = String(rawText || "").trim();
    if (!text || isSending) {
      return;
    }

    appendUserMessage(text);
    setInputValue("");
    setIsSending(true);

    const payload = {
      session_id: sessionId,
      message: text,
    };

    if (mode !== "auto") {
      payload.context = { mode };
    } else if (shouldForceQuizMode(text, mode, lastAssistantMessage)) {
      payload.context = { mode: "quiz" };
    }

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const rawBody = await response.text();
      let data;
      try {
        data = JSON.parse(rawBody);
      } catch {
        data = { type: "chat", message: rawBody };
      }

      if (!response.ok) {
        const message =
          typeof data?.detail === "string"
            ? data.detail
            : `백엔드 오류 (${response.status})`;
        appendAssistantMessage({ kind: "error", text: message, data });
        return;
      }

      const normalized = normalizeApiResponse(data);
      appendAssistantMessage(normalized);
    } catch (error) {
      appendAssistantMessage({
        kind: "error",
        text: `서버와 통신할 수 없습니다. ${error instanceof Error ? error.message : ""}`,
      });
    } finally {
      setIsSending(false);
    }
  };

  const onSubmit = (event) => {
    event.preventDefault();
    sendMessage(inputValue);
  };

  return (
    <div className="page">
      <aside className="sidebar">
        <h1>TradeOnboarding</h1>
        <p className="muted">무역 실무 온보딩 AI 코치</p>

        <label className="field-label" htmlFor="mode-select">
          라우팅 모드
        </label>
        <select
          id="mode-select"
          value={mode}
          onChange={(event) => setMode(event.target.value)}
          className="mode-select"
        >
          {MODE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <div className="session-box">
          <span>Session ID</span>
          <code>{sessionId}</code>
        </div>

        <button type="button" className="reset-btn" onClick={resetConversation}>
          새 대화 시작
        </button>
      </aside>

      <main className="chat-panel">
        <header className="chat-header">
          <h2>채팅</h2>
          <p className="muted">
            퀴즈/이메일/리스크 응답을 단일 UI에서 렌더링합니다.
          </p>
        </header>

        <section className="message-list">
          {messages.length === 0 ? (
            <div className="empty-state">
              <p>예시 입력: "무역실무 퀴즈내줘", "이메일 초안 영어로 만들어줘", "선적이 늦어져요"</p>
            </div>
          ) : null}

          {messages.map((message) => (
            <article
              key={message.id}
              className={message.role === "user" ? "message user" : "message assistant"}
            >
              <div className="message-label">{message.role === "user" ? "사용자" : "AI 비서"}</div>
              {message.role === "user" ? (
                <p className="multiline">{message.text}</p>
              ) : (
                <AssistantContent message={message} onQuickAnswer={sendMessage} />
              )}
            </article>
          ))}

          {isSending ? <p className="muted">응답 생성 중...</p> : null}
          <div ref={listBottomRef} />
        </section>

        <form className="composer" onSubmit={onSubmit}>
          <input
            type="text"
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            placeholder="메시지를 입력하세요"
            disabled={isSending}
          />
          <button type="submit" disabled={isSending || !inputValue.trim()}>
            전송
          </button>
        </form>
      </main>
    </div>
  );
}
