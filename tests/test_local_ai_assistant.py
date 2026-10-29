# ============================================================
# شرح الملف: tests/test_local_ai_assistant.py
# اختبارات خفيفة للتوجيه المحلي للمساعد دون تشغيل واجهة Qt.
# ============================================================
from ai.intent_router import route_query

def test_local_ai_intent_routing():
    assert route_query("ما هي أعلى المصاريف؟").name == "TOP_EXPENSES"
    assert route_query("لماذا مشروع PRG-007 متأخر؟").project_id == "PRG-007"
    assert route_query("ما هي الديون؟").name == "DEBTS"
    assert route_query("أعطني ملخص الشركة").name == "COMPANY_SUMMARY"
