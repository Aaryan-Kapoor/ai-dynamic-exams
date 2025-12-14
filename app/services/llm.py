from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class GeneratedQuestion:
    question: str
    ideal_answer: str


@dataclass(frozen=True)
class GradedAnswer:
    correctness: float  # 0..1
    is_correct: bool
    feedback: str


class LLMClient:
    def generate_question(
        self,
        *,
        context: str,
        difficulty: int,
        avoid_questions: list[str],
    ) -> GeneratedQuestion:
        raise NotImplementedError

    def grade_answer(
        self,
        *,
        question: str,
        ideal_answer: str,
        context: str,
        student_answer: str,
    ) -> GradedAnswer:
        raise NotImplementedError


def _coerce_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("LLM did not return JSON")
    return json.loads(match.group(0))


class OpenAICompatLLMClient(LLMClient):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout_seconds
        self._client = httpx.Client(timeout=self._timeout)

    def _chat(self, messages: list[dict[str, str]]) -> str:
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        resp = self._client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def generate_question(
        self,
        *,
        context: str,
        difficulty: int,
        avoid_questions: list[str],
    ) -> GeneratedQuestion:
        avoid = "\n".join(f"- {q[:200]}" for q in avoid_questions[-25:]) or "- (none)"
        system = (
            "You are an expert university examiner. "
            "Generate ONE question based only on the provided lecture context. "
            "Return strict JSON."
        )
        user = f"""
Lecture context:
{context}

Difficulty (1 easiest .. 5 hardest): {difficulty}

Avoid repeating these questions (do not copy them, do not paraphrase too closely):
{avoid}

Return JSON with:
{{
  "question": "...",
  "ideal_answer": "..."
}}
""".strip()
        content = self._chat(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        obj = _coerce_json(content)
        question = str(obj.get("question", "")).strip()
        ideal_answer = str(obj.get("ideal_answer", "")).strip()
        if not question:
            raise ValueError("LLM returned empty question")
        return GeneratedQuestion(question=question, ideal_answer=ideal_answer)

    def grade_answer(
        self,
        *,
        question: str,
        ideal_answer: str,
        context: str,
        student_answer: str,
    ) -> GradedAnswer:
        system = (
            "You are a strict but fair examiner. "
            "Grade the student's answer using the lecture context and the ideal answer. "
            "Return strict JSON only."
        )
        user = f"""
Lecture context:
{context}

Question:
{question}

Ideal answer:
{ideal_answer}

Student answer:
{student_answer}

Return JSON with:
{{
  "correctness": 0.0,
  "is_correct": true,
  "feedback": "..."
}}
Correctness must be between 0 and 1.
""".strip()
        content = self._chat(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        obj = _coerce_json(content)
        correctness_raw = obj.get("correctness", 0.0)
        try:
            correctness = float(correctness_raw)
        except Exception:
            correctness = 0.0
        correctness = max(0.0, min(1.0, correctness))
        is_correct = bool(obj.get("is_correct", correctness >= 0.5))
        feedback = str(obj.get("feedback", "")).strip()
        return GradedAnswer(correctness=correctness, is_correct=is_correct, feedback=feedback)


class MockLLMClient(LLMClient):
    def __init__(self, *, seed: int = 0) -> None:
        self._rng = random.Random(seed)

    def generate_question(
        self,
        *,
        context: str,
        difficulty: int,
        avoid_questions: list[str],
    ) -> GeneratedQuestion:
        sentences = [s.strip() for s in re.split(r"[.\n]{1,}", context) if s.strip()]
        pick = self._rng.choice(sentences) if sentences else "the provided lecture context"
        question = f"Explain: {pick[:180]}?"
        ideal = pick[:300]
        return GeneratedQuestion(question=question, ideal_answer=ideal)

    def grade_answer(
        self,
        *,
        question: str,
        ideal_answer: str,
        context: str,
        student_answer: str,
    ) -> GradedAnswer:
        def toks(s: str) -> set[str]:
            return set(re.findall(r"[a-zA-Z]{3,}", (s or "").lower()))

        ideal = toks(ideal_answer or context)
        ans = toks(student_answer)
        if not ideal:
            return GradedAnswer(correctness=0.0, is_correct=False, feedback="No reference material.")
        overlap = len(ideal & ans) / max(1, len(ideal))
        correctness = max(0.0, min(1.0, overlap * 1.5))
        is_correct = correctness >= 0.55
        feedback = "Good." if is_correct else "Needs improvement."
        return GradedAnswer(correctness=correctness, is_correct=is_correct, feedback=feedback)


class FallbackLLMClient(LLMClient):
    def __init__(self, *, primary: LLMClient, fallback: LLMClient) -> None:
        self._primary = primary
        self._fallback = fallback

    def generate_question(
        self,
        *,
        context: str,
        difficulty: int,
        avoid_questions: list[str],
    ) -> GeneratedQuestion:
        try:
            return self._primary.generate_question(
                context=context, difficulty=difficulty, avoid_questions=avoid_questions
            )
        except Exception:
            return self._fallback.generate_question(
                context=context, difficulty=difficulty, avoid_questions=avoid_questions
            )

    def grade_answer(
        self,
        *,
        question: str,
        ideal_answer: str,
        context: str,
        student_answer: str,
    ) -> GradedAnswer:
        try:
            return self._primary.grade_answer(
                question=question,
                ideal_answer=ideal_answer,
                context=context,
                student_answer=student_answer,
            )
        except Exception:
            return self._fallback.grade_answer(
                question=question,
                ideal_answer=ideal_answer,
                context=context,
                student_answer=student_answer,
            )
