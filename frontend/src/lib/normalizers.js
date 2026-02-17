function parseJsonSafely(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function parseJsonFlexible(rawText) {
  if (typeof rawText !== "string") {
    return null;
  }

  const trimmed = rawText.trim();
  if (!trimmed) {
    return null;
  }

  const candidates = [trimmed];

  const fencedMatches = [...trimmed.matchAll(/```(?:json)?\s*([\s\S]*?)```/gi)];
  for (const match of fencedMatches) {
    if (match[1]?.trim()) {
      candidates.push(match[1].trim());
    }
  }

  const objectStart = trimmed.indexOf("{");
  const objectEnd = trimmed.lastIndexOf("}");
  if (objectStart >= 0 && objectEnd > objectStart) {
    candidates.push(trimmed.slice(objectStart, objectEnd + 1));
  }

  const arrayStart = trimmed.indexOf("[");
  const arrayEnd = trimmed.lastIndexOf("]");
  if (arrayStart >= 0 && arrayEnd > arrayStart) {
    candidates.push(trimmed.slice(arrayStart, arrayEnd + 1));
  }

  for (const candidate of candidates) {
    const parsed = parseJsonSafely(candidate);
    if (parsed !== null) {
      return parsed;
    }
  }

  return null;
}

function extractQuizQuestions(payload) {
  if (Array.isArray(payload)) {
    return payload.filter((item) => item && typeof item === "object" && item.question);
  }

  if (payload && typeof payload === "object") {
    if (Array.isArray(payload.questions)) {
      return payload.questions.filter((item) => item && typeof item === "object" && item.question);
    }
    if (Array.isArray(payload.answer)) {
      return payload.answer.filter((item) => item && typeof item === "object" && item.question);
    }
  }

  return [];
}

export function normalizeRiskFactors(report = {}) {
  const scoring = report.risk_scoring && typeof report.risk_scoring === "object" ? report.risk_scoring : {};
  const rawFactors = scoring.risk_factors ?? report.risk_factors ?? [];

  let factorEntries = [];
  if (Array.isArray(rawFactors)) {
    factorEntries = rawFactors.map((factor, index) => [`factor_${index}`, factor]);
  } else if (rawFactors && typeof rawFactors === "object") {
    factorEntries = Object.entries(rawFactors);
  }

  return factorEntries
    .map(([fallbackName, factor]) => {
      if (!factor || typeof factor !== "object") {
        return null;
      }

      const impact = Number.isFinite(Number(factor.impact)) ? Number(factor.impact) : 0;
      const likelihood = Number.isFinite(Number(factor.likelihood)) ? Number(factor.likelihood) : 0;

      let score = Number(factor.score);
      if (!Number.isFinite(score)) {
        score = Number(factor.risk_score);
      }
      if (!Number.isFinite(score)) {
        score = impact * likelihood;
      }
      if (!Number.isFinite(score)) {
        score = 0;
      }

      return {
        name:
          String(factor.name_kr || factor.name || fallbackName || "unknown").trim() || "unknown",
        impact,
        likelihood,
        score,
        reason: String(factor.reason || factor.reasoning || "").trim(),
        suggestions: Array.isArray(factor.mitigation_suggestions)
          ? factor.mitigation_suggestions.map(String).filter(Boolean)
          : [],
      };
    })
    .filter(Boolean);
}

export function normalizeApiResponse(raw) {
  if (!raw || typeof raw !== "object") {
    return {
      kind: "text",
      text: "응답 형식이 올바르지 않습니다.",
    };
  }

  if (raw.type === "report" && raw.report && typeof raw.report === "object") {
    return {
      kind: "report",
      report: raw.report,
      text: typeof raw.message === "string" ? raw.message : "",
    };
  }

  const message =
    typeof raw.message === "string"
      ? raw.message
      : JSON.stringify(raw.message ?? raw, null, 2);

  const parsedMessage = parseJsonFlexible(message);
  const quizQuestions = extractQuizQuestions(parsedMessage);

  if (quizQuestions.length > 0) {
    return {
      kind: "quiz",
      questions: quizQuestions,
      text: "퀴즈가 생성되었습니다.",
    };
  }

  if (parsedMessage && typeof parsedMessage === "object") {
    if (!Array.isArray(parsedMessage) && parsedMessage.error) {
      return {
        kind: "error",
        data: parsedMessage,
        text: String(parsedMessage.error || "요청 처리 중 오류가 발생했습니다."),
      };
    }

    if (!Array.isArray(parsedMessage) && parsedMessage.email_content) {
      return {
        kind: "email",
        data: parsedMessage,
        text: "이메일 초안이 생성되었습니다.",
      };
    }

    return {
      kind: "json",
      data: parsedMessage,
      text: message,
    };
  }

  return {
    kind: "text",
    text: message || "응답이 비어 있습니다.",
  };
}

export function shouldForceQuizMode(userInput, mode, lastAssistantMessage) {
  if (mode !== "auto") {
    return false;
  }

  if (!lastAssistantMessage || lastAssistantMessage.kind !== "quiz") {
    return false;
  }

  const normalized = String(userInput || "").trim().toLowerCase();
  if (!normalized) {
    return false;
  }

  if (/^[1-4]\s*번?$/.test(normalized)) {
    return true;
  }

  return ["정답", "해설", "힌트", "다음 문제", "다음문제"].some((keyword) =>
    normalized.includes(keyword)
  );
}
