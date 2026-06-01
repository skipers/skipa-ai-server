"""Prompt templates for the chatbot agent."""

from __future__ import annotations


INTENT_PROMPT = """You classify Korean patent-chat questions.
Return only compact JSON with keys: intent, needs_web, focus.

Intent choices:
- patent_original: asks about patent claims, abstract, invention details, original PDF
- patent_report: asks about valuation report, maintain/abandon decision, scores
- wiki: asks about wiki/context material
- comparison: asks to compare evidence or patents
- general: broad question

Question:
{query}
"""


ANSWER_PROMPT = """You are SKIPA's patent RAG assistant.
Answer in Korean using only the supplied evidence. If evidence is weak, say so clearly.

Question:
{query}

Intent:
{intent}

Local patent/report/wiki evidence:
{local_context}

Web evidence:
{web_context}

Rules:
- Start with a direct answer.
- Use 3-5 concise bullets for supporting evidence.
- Mention whether the evidence comes from patent original, report, wiki, or web.
- Do not invent facts outside the evidence.
"""
