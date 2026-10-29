# ============================================================
# شرح الملف: services/executive_control_service.py
# محرك الرقابة التنفيذية للمرحلة الخامسة والأخيرة.
# يكتشف المخاطر من البيانات الموجودة، يمنع التنبيهات المكررة،
# وينشئ إجراءات حوكمة قابلة للمتابعة دون إنشاء مصدر بيانات ثانٍ.
# ============================================================
"""Executive control engine for BuildOffice Pro final phase."""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Any

from core.logging_config import logger
from repositories.db import get_connection

from .analytics_service import smart_analytics
from .settings_service import (
    alert_collection_rate,
    alert_cost_progress_gap,
    alert_document_days,
    alert_progress_gap,
    setting_bool,
)


def _f(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _fingerprint(project_id: str | None, code: str, source_id: str | None = None) -> str:
    raw = "|".join(str(x or "") for x in (project_id, code, source_id))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _severity_rank(value: str) -> int:
    return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}.get(str(value).upper(), 0)


def _collect_findings(conn) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not setting_bool("intelligence_enabled", True):
        return findings

    progress_gap = alert_progress_gap()
    collection_threshold = alert_collection_rate() / 100.0
    cost_gap = alert_cost_progress_gap()
    document_days = alert_document_days()

    # Portfolio/project signals already calculated by the analytics layer.
    try:
        data = smart_analytics(conn)
        for project in data.get("projects", []):
            pid = str(project.get("project_id") or "")
            name = str(project.get("project_name") or pid)
            if not pid:
                continue
            progress = _f(project.get("progress"))
            planned = _f(project.get("planned_progress"))
            cost_pct = _f(project.get("cost_pct"))
            earned = _f(project.get("earned"))
            received = _f(project.get("received"))

            if project.get("status") == "Active" and planned - progress > progress_gap:
                findings.append({"project_id": pid, "code": "SCHEDULE_GAP", "severity": "HIGH",
                                 "title": f"Schedule delay: {name}",
                                 "message": f"Physical progress is {planned-progress:.1f}% behind the planned schedule.",
                                 "source_type": "Project", "source_id": pid})
            if progress > 0 and cost_pct - progress > cost_gap:
                findings.append({"project_id": pid, "code": "COST_PROGRESS_GAP", "severity": "HIGH",
                                 "title": f"Cost ahead of progress: {name}",
                                 "message": f"Cost consumption is {cost_pct-progress:.1f}% ahead of physical progress.",
                                 "source_type": "Project", "source_id": pid})
            if earned > 0 and received / earned < collection_threshold:
                findings.append({"project_id": pid, "code": "COLLECTION_RISK", "severity": "MEDIUM",
                                 "title": f"Collection risk: {name}",
                                 "message": f"Collection rate is {(received/earned)*100:.1f}%, below the configured threshold of {collection_threshold*100:.1f}%.",
                                 "source_type": "Project", "source_id": pid})
    except (sqlite3.Error, KeyError, TypeError, ValueError):
        logger.exception("Executive control scan failed while collecting a signal")

    # Governance registers.
    try:
        rows = conn.execute("""SELECT milestone_id, project_id, name, planned_date FROM project_milestones
                              WHERE status NOT IN ('Completed','Cancelled') AND date(planned_date) < date('now')""").fetchall()
        for r in rows:
            findings.append({"project_id": r["project_id"], "code": "OVERDUE_MILESTONE", "severity": "HIGH",
                             "title": f"Overdue milestone: {r['name']}", "message": f"Milestone planned for {r['planned_date']} is overdue.",
                             "source_type": "Milestone", "source_id": r["milestone_id"]})
    except (sqlite3.Error, KeyError, TypeError, ValueError):
        logger.exception("Executive control scan failed while collecting a signal")
    try:
        rows = conn.execute("""SELECT action_id, project_id, title, due_date FROM governance_actions
                              WHERE status NOT IN ('Completed','Cancelled') AND date(due_date) < date('now')""").fetchall()
        for r in rows:
            findings.append({"project_id": r["project_id"], "code": "OVERDUE_ACTION", "severity": "HIGH",
                             "title": f"Overdue action: {r['title']}", "message": f"Corrective action due {r['due_date']} is overdue.",
                             "source_type": "Action", "source_id": r["action_id"]})
    except (sqlite3.Error, KeyError, TypeError, ValueError):
        logger.exception("Executive control scan failed while collecting a signal")
    try:
        rows = conn.execute("""SELECT risk_id, project_id, title, score FROM project_risks
                              WHERE status IN ('Open','Monitoring') AND score >= 12""").fetchall()
        for r in rows:
            findings.append({"project_id": r["project_id"], "code": "HIGH_RISK", "severity": "CRITICAL" if int(r["score"] or 0) >= 20 else "HIGH",
                             "title": f"High project risk: {r['title']}", "message": f"Risk score is {int(r['score'] or 0)}/25.",
                             "source_type": "Risk", "source_id": r["risk_id"]})
    except (sqlite3.Error, KeyError, TypeError, ValueError):
        logger.exception("Executive control scan failed while collecting a signal")

    # Compliance and procurement signals.
    try:
        rows = conn.execute("""SELECT document_id, owner_id, file_name, expiry_date FROM documents
                              WHERE owner_type='project' AND expiry_date IS NOT NULL
                              AND date(expiry_date) <= date('now', ?)""", (f"+{document_days} day",)).fetchall()
        for r in rows:
            expired = str(r["expiry_date"]) < datetime.now(timezone.utc).date().isoformat()
            findings.append({"project_id": r["owner_id"], "code": "DOCUMENT_EXPIRED" if expired else "DOCUMENT_EXPIRING",
                             "severity": "CRITICAL" if expired else "MEDIUM",
                             "title": f"{'Expired' if expired else 'Expiring'} document: {r['file_name'] or r['document_id']}",
                             "message": f"Document expiry date: {r['expiry_date']}.", "source_type": "Document", "source_id": r["document_id"]})
    except (sqlite3.Error, KeyError, TypeError, ValueError):
        logger.exception("Executive control scan failed while collecting a signal")
    try:
        rows = conn.execute("""SELECT purchase_order_id, order_number, project_id, expected_date FROM purchase_orders
                              WHERE project_id IS NOT NULL AND status IN ('Approved','Submitted','Partially Received')
                              AND expected_date IS NOT NULL AND date(expected_date) < date('now')""").fetchall()
        for r in rows:
            findings.append({"project_id": r["project_id"], "code": "OVERDUE_PURCHASE", "severity": "MEDIUM",
                             "title": f"Overdue purchase order: {r['order_number']}",
                             "message": f"Expected delivery date {r['expected_date']} has passed.",
                             "source_type": "PurchaseOrder", "source_id": r["purchase_order_id"]})
    except (sqlite3.Error, KeyError, TypeError, ValueError):
        logger.exception("Executive control scan failed while collecting a signal")

    return findings


def run_governance_scan() -> dict[str, Any]:
    """Materialize current intelligence findings into deduplicated alerts and actions."""
    conn = get_connection()
    try:
        findings = _collect_findings(conn)
        active_fingerprints: set[str] = set()
        created_alerts = 0
        refreshed_alerts = 0
        created_actions = 0
        notifications = 0

        for finding in findings:
            fp = _fingerprint(finding.get("project_id"), finding["code"], finding.get("source_id"))
            active_fingerprints.add(fp)
            existing = conn.execute("SELECT alert_id, severity, message, is_active FROM intelligence_alerts WHERE fingerprint=?", (fp,)).fetchone()
            if existing:
                conn.execute("""UPDATE intelligence_alerts SET severity=?, title=?, message=?, last_seen_at=CURRENT_TIMESTAMP,
                               is_active=1, resolved_at=NULL WHERE alert_id=?""",
                             (finding["severity"], finding["title"], finding["message"], existing["alert_id"]))
                refreshed_alerts += 1
                was_active = bool(existing["is_active"])
            else:
                alert_id = _fingerprint(None, "ALERT", fp)
                conn.execute("""INSERT INTO intelligence_alerts
                    (alert_id,fingerprint,project_id,severity,title,message,source_type,source_id,is_active)
                    VALUES(?,?,?,?,?,?,?,?,1)""",
                    (alert_id, fp, finding.get("project_id"), finding["severity"], finding["title"], finding["message"], finding.get("source_type"), finding.get("source_id")))
                created_alerts += 1
                was_active = False

            if not was_active:
                conn.execute("INSERT INTO notifications(title,message,severity,entity,entity_id) VALUES(?,?,?,?,?)",
                             (finding["title"], finding["message"], finding["severity"], finding.get("source_type", "Project"), finding.get("source_id")))
                notifications += 1

            pid = finding.get("project_id")
            if pid:
                open_action = conn.execute("""SELECT action_id FROM governance_actions
                    WHERE project_id=? AND source_type=? AND source_id=? AND status NOT IN ('Completed','Cancelled') LIMIT 1""",
                    (pid, finding.get("source_type"), finding.get("source_id"))).fetchone()
                if not open_action and _severity_rank(finding["severity"]) >= 3:
                    from core.id_service import next_sequence_id
                    aid = next_sequence_id(conn, "ACT", digits=8)
                    priority = 1 if finding["severity"] == "CRITICAL" else 2
                    conn.execute("""INSERT INTO governance_actions(action_id,project_id,title,owner,due_date,status,priority,source_type,source_id,notes)
                        VALUES(?,?,?,?,date('now','+7 day'),'Open',?,?,?,?)""",
                        (aid, pid, f"Resolve: {finding['title']}", "Project Manager", priority, finding.get("source_type"), finding.get("source_id"), finding["message"]))
                    created_actions += 1

        if active_fingerprints:
            placeholders = ",".join("?" for _ in active_fingerprints)
            conn.execute(f"UPDATE intelligence_alerts SET is_active=0, resolved_at=CURRENT_TIMESTAMP WHERE is_active=1 AND fingerprint NOT IN ({placeholders})", tuple(active_fingerprints))
        else:
            conn.execute("UPDATE intelligence_alerts SET is_active=0, resolved_at=CURRENT_TIMESTAMP WHERE is_active=1")

        conn.commit()
        critical = sum(1 for x in findings if x["severity"] == "CRITICAL")
        high = sum(1 for x in findings if x["severity"] == "HIGH")
        medium = sum(1 for x in findings if x["severity"] == "MEDIUM")
        return {"total": len(findings), "critical": critical, "high": high, "medium": medium,
                "created_alerts": created_alerts, "refreshed_alerts": refreshed_alerts,
                "created_actions": created_actions, "notifications": notifications}
    finally:
        conn.close()


def portfolio_control_snapshot() -> dict[str, Any]:
    """Return an executive health score based on active alerts across the portfolio."""
    conn = get_connection()
    try:
        data = smart_analytics(conn)
        rows = conn.execute("SELECT severity, COUNT(*) AS n FROM intelligence_alerts WHERE is_active=1 GROUP BY severity").fetchall()
        counts = {str(r["severity"]): int(r["n"] or 0) for r in rows}
        score = max(0, 100 - counts.get("CRITICAL", 0) * 20 - counts.get("HIGH", 0) * 10 - counts.get("MEDIUM", 0) * 4)
        return {"score": score, "critical": counts.get("CRITICAL", 0), "high": counts.get("HIGH", 0),
                "medium": counts.get("MEDIUM", 0), "portfolio": data.get("portfolio", {})}
    finally:
        conn.close()
