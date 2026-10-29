# ============================================================
# شرح الملف: ai/intent_router.py
# يحدد نية السؤال محليًا دون نموذج سحابي أو اتصال بالإنترنت.
# ============================================================
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class QueryIntent:
    name: str
    project_id: str | None = None
    confidence: float = 0.0
def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text or "")).lower()
    text = re.sub(r"[إأآا]", "ا", text).replace("ى", "ي").replace("ة", "ه")
    text = re.sub(r"[ًٌٍَُِّْـ]", "", text)
    return re.sub(r"\s+", " ", text).strip()
def _project_id(q: str) -> str | None:
    m = re.search(r"\b(prg[-_ ]?\d+)\b", q, re.IGNORECASE)
    if m:
        raw = m.group(1).upper().replace("_", "-").replace(" ", "-")
        return raw if "-" in raw else raw[:3] + "-" + raw[3:]
    m = re.search(r"(?:project|مشروع)\s*#?\s*(\d+)\b", q)
    return f"PRG-{int(m.group(1)):03d}" if m else None
def route_query(text: str) -> QueryIntent:
    q = _normalize(text); pid = _project_id(q)
    rules = [
        ("LOSING_PROJECTS", ("losing", "loss", "negative margin", "خاسر", "خساره", "خسائر"), .96),
        ("PROJECT_HEALTH", ("why is", "why does", "performing", "health", "status", "وضع", "حاله", "اداء", "لماذا"), .95),
        ("TOP_EXPENSES", ("highest expense", "most expensive", "highest spending", "اعلى مصاريف", "اعلي المصاريف", "اكثر صرف", "اكبر مصروف"), .95),
        ("PROJECT_FINANCIAL", ("financial", "budget", "cost", "spent", "spend", "expense", "ربحي", "ميزاني", "تكلف", "صرف", "مصاريف", "ربح"), .92),
        ("PROJECT_PROGRESS", ("progress", "executed", "remaining", "situation", "تقدم", "انجاز", "منجز", "متبقي", "وضعيه"), .92),
        ("WORKFORCE", ("attendance", "payroll", "labor", "worker", "staff", "hours", "حضور", "رواتب", "عمال", "موظف", "ساعات"), .90),
        ("RECEIVABLES", ("receivable", "collection", "client payment", "مستحقات", "تحصيل", "قبض", "عملاء"), .90),
        ("DEBTS", ("debt", "owe", "liabilit", "دين", "ديون", "مدين", "التزامات"), .90),
        ("VEHICLES", ("vehicle", "fleet", "fuel", "maintenance", "مركب", "اسطول", "وقود", "صيانه"), .88),
        ("DOCUMENTS", ("document", "expiry", "compliance", "وثائق", "وثيقه", "مستند", "انتهاء"), .88),
        ("MATERIALS", ("material", "consumption", "مواد", "استهلاك"), .88),
        ("BOQ", ("boq", "métré", "metre", "quantity", "item", "جدول الكميات", "متر", "بند", "كميه"), .88),
        ("CASH_FLOW", ("cash flow", "cashflow", "cash", "نقد", "تدفق نقدي"), .90),
        ("ALERTS", ("attention", "urgent", "risk", "alert", "problem", "danger", "انتباه", "عاجل", "خطر", "مشاكل", "مشكل"), .90),
        ("COMPANY_SUMMARY", ("company", "company summary", "الشركه", "الشركة", "ملخص الشركه", "ملخص الشركة"), .86),
    ]
    if any(k in q for k in ("all projects", "every project", "كل المشاريع", "المشاريع كلها")) and any(k in q for k in ("health", "status", "وضع", "حال", "اداء")):
        return QueryIntent("PROJECT_PORTFOLIO", pid, .95)
    for name, keys, confidence in rules:
        if any(k in q for k in keys): return QueryIntent(name, pid, confidence)
    return QueryIntent("GENERAL", pid, .25)
