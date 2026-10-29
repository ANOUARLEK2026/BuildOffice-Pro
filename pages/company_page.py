# ============================================================
# شرح الملف: pages/company_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على الحقول القديمة، مع توسيع الصفحة لتصبح مصدر الهوية المركزي للشركة.
# ============================================================
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.config import ROOT_DIR
from core.i18n import translate_text
from repositories.db import get_connection
from theme import set_theme_style

from .base_page import BasePage, SectionCard, set_button


class CompanyPage(BasePage):
    """Central company identity and profile workspace.

    The page is intentionally more than a form: it acts as the single source of
    truth for the company identity shown by the application and prepared for
    reports, documents and future exports.
    """

    from typing import ClassVar

    FIELD_DEFINITIONS: ClassVar[tuple[tuple[str, str], ...]] = (
        ("company name", "Company name"),
        ("company name ar", "Company name (Arabic)"),
        ("legal form", "Legal form"),
        ("owner", "Owner / manager"),
        ("activity", "Main activity"),
        ("wilaya", "Wilaya"),
        ("postal code", "Postal code"),
        ("address", "Address"),
        ("phone 1", "Phone 1"),
        ("phone 2", "Phone 2"),
        ("fax", "Fax"),
        ("email 1", "Email 1"),
        ("email 2", "Email 2"),
        ("website", "Website"),
        ("reg com", "Commercial register (RC)"),
        ("nif", "NIF"),
        ("nis", "NIS"),
        ("bea", "BEA reference"),
        ("cpa", "CPA reference"),
        ("bank name", "Primary bank"),
        ("bank account", "Bank account / RIB"),
        ("bank branch", "Bank branch"),
        ("notes", "Internal notes"),
    )

    def __init__(self):
        super().__init__(
            translate_text("Company"),
            translate_text("Central company identity, legal profile and document-ready information"),
        )
        self.ed: dict[str, QLineEdit] = {}
        self.logo_path = ""
        self._build_ui()
        self._load()

    # ============================================================
    # Interface
    # ============================================================
    def _build_ui(self):
        """Build the company identity workspace inside a dedicated scroll viewport.

        The application stack is intentionally not globally scrollable because many
        pages have their own table/view scrolling. Company Identity is a dense form,
        so this page owns one clean vertical scroll area for its content. This avoids
        clipping when the window is shorter than the complete identity profile.
        """
        scroll = QScrollArea()
        scroll.setObjectName("companyPageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidgetResizable(True)
        scroll.viewport().setObjectName("companyPageViewport")

        content = QWidget()
        content.setObjectName("companyPageContent")
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 2, 12)
        body.setSpacing(13)
        scroll.setWidget(content)
        self.body.addWidget(scroll)

        intro = QFrame()
        intro.setObjectName("companyIntro")
        set_theme_style(intro, """
            QFrame#companyIntro {
                background: @surface@;
                border: 1px solid @border@;
                border-left: 4px solid @primary@;
                border-radius: 12px;
            }
            QLabel#companyIntroTitle {
                color: @text_primary@;
                background: transparent;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#companyIntroText {
                color: @text_secondary@;
                background: transparent;
                font-size: 11px;
            }
            QLabel#companyPurpose {
                color: @text_primary@;
                background: @surface_alt@;
                border: 1px solid @border@;
                border-radius: 8px;
                padding: 7px 9px;
                font-size: 11px;
            }
        """)
        il = QVBoxLayout(intro)
        il.setContentsMargins(14, 11, 14, 11)
        il.setSpacing(4)
        title = QLabel(translate_text("Company identity center"))
        title.setObjectName("companyIntroTitle")
        il.addWidget(title)
        text = QLabel(translate_text(
            "Keep one authoritative company profile for the application, reports, documents, correspondence and future exports."
        ))
        text.setObjectName("companyIntroText")
        text.setWordWrap(True)
        il.addWidget(text)
        purpose = QLabel(translate_text(
            "Purpose: enter the company data once, then reuse it everywhere instead of repeating or retyping identity details."
        ))
        purpose.setObjectName("companyPurpose")
        purpose.setWordWrap(True)
        il.addWidget(purpose)
        body.addWidget(intro)

        top = QHBoxLayout()
        top.setSpacing(12)

        identity = SectionCard(
            translate_text("Identity & activity"),
            translate_text("The information that defines who the company is and what it does."),
            "@primary@",
        )
        identity.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(7)
        self._add_pair(grid, 0, 0, "company name", "Company name")
        self._add_pair(grid, 0, 2, "company name ar", "Company name (Arabic)")
        self._add_pair(grid, 1, 0, "legal form", "Legal form")
        self._add_pair(grid, 1, 2, "owner", "Owner / manager")
        self._add_pair(grid, 2, 0, "activity", "Main activity")
        self._add_pair(grid, 2, 2, "wilaya", "Wilaya")
        self._add_pair(grid, 3, 0, "postal code", "Postal code")
        self._add_full(grid, 4, "address", "Address")
        identity.root_layout.addLayout(grid)
        top.addWidget(identity, 1)

        preview = SectionCard(
            translate_text("Identity preview"),
            translate_text("This is how the company identity is represented inside BuildOffice Pro."),
            "@info@",
        )
        preview.setMinimumWidth(300)
        preview.setMaximumWidth(390)
        preview.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        pv = QVBoxLayout()
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(7)
        ph = QHBoxLayout()
        ph.setSpacing(10)
        self.logo = QLabel()
        self.logo.setObjectName("companyLogoPreview")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setFixedSize(68, 68)
        ph.addWidget(self.logo)
        names = QVBoxLayout()
        names.setSpacing(2)
        self.preview_name = QLabel()
        self.preview_name.setObjectName("companyPreviewName")
        self.preview_name.setWordWrap(True)
        names.addWidget(self.preview_name)
        self.preview_ar = QLabel()
        self.preview_ar.setObjectName("companyPreviewAr")
        self.preview_ar.setWordWrap(True)
        names.addWidget(self.preview_ar)
        self.preview_activity = QLabel()
        self.preview_activity.setObjectName("companyPreviewMeta")
        self.preview_activity.setWordWrap(True)
        names.addWidget(self.preview_activity)
        ph.addLayout(names, 1)
        pv.addLayout(ph)
        self.profile_status = QLabel()
        self.profile_status.setObjectName("companyProfileStatus")
        self.profile_status.setWordWrap(True)
        pv.addWidget(self.profile_status)
        logo_actions = QHBoxLayout()
        self.logo_btn = QPushButton(translate_text("Change logo"))
        set_button(self.logo_btn, "secondary")
        self.logo_btn.clicked.connect(self._choose_logo)
        reset_logo = QPushButton(translate_text("Use default logo"))
        set_button(reset_logo, "secondary")
        reset_logo.clicked.connect(self._reset_logo)
        logo_actions.addWidget(self.logo_btn)
        logo_actions.addWidget(reset_logo)
        pv.addLayout(logo_actions)
        preview.root_layout.addLayout(pv)
        top.addWidget(preview, 0)
        body.addLayout(top)

        contact = SectionCard(
            translate_text("Contact & digital presence"),
            translate_text("Official channels used for communication and identification."),
            "@info@",
        )
        cg = QGridLayout()
        cg.setContentsMargins(0, 0, 0, 0)
        cg.setHorizontalSpacing(10)
        cg.setVerticalSpacing(7)
        self._add_pair(cg, 0, 0, "phone 1", "Phone 1")
        self._add_pair(cg, 0, 2, "phone 2", "Phone 2")
        self._add_pair(cg, 1, 0, "fax", "Fax")
        self._add_pair(cg, 1, 2, "website", "Website")
        self._add_pair(cg, 2, 0, "email 1", "Email 1")
        self._add_pair(cg, 2, 2, "email 2", "Email 2")
        contact.root_layout.addLayout(cg)
        body.addWidget(contact)

        compliance = SectionCard(
            translate_text("Legal & banking profile"),
            translate_text("Registration identifiers and payment references kept together for document workflows."),
            "@success@",
        )
        lg = QGridLayout()
        lg.setContentsMargins(0, 0, 0, 0)
        lg.setHorizontalSpacing(10)
        lg.setVerticalSpacing(7)
        self._add_pair(lg, 0, 0, "reg com", "Commercial register (RC)")
        self._add_pair(lg, 0, 2, "nif", "NIF")
        self._add_pair(lg, 1, 0, "nis", "NIS")
        self._add_pair(lg, 1, 2, "bank name", "Primary bank")
        self._add_pair(lg, 2, 0, "bank account", "Bank account / RIB")
        self._add_pair(lg, 2, 2, "bank branch", "Bank branch")
        self._add_pair(lg, 3, 0, "bea", "BEA reference")
        self._add_pair(lg, 3, 2, "cpa", "CPA reference")
        compliance.root_layout.addLayout(lg)
        body.addWidget(compliance)

        notes = SectionCard(
            translate_text("Internal notes"),
            translate_text("Optional notes for company administration. These do not replace legal records."),
            "@warning@",
        )
        ng = QGridLayout()
        ng.setContentsMargins(0, 0, 0, 0)
        self._add_full(ng, 0, "notes", "Internal notes")
        notes.root_layout.addLayout(ng)
        body.addWidget(notes)

        actions = QFrame()
        actions.setObjectName("pageToolbar")
        al = QHBoxLayout(actions)
        al.setContentsMargins(8, 5, 8, 5)
        al.setSpacing(8)
        hint = QLabel(translate_text("Company identity is shared by the application shell and can be reused by document/report workflows."))
        hint.setObjectName("secondaryText")
        hint.setWordWrap(True)
        al.addWidget(hint, 1)
        self.save_btn = QPushButton(translate_text("Save company profile"))
        set_button(self.save_btn, "primary")
        self.save_btn.setMinimumHeight(34)
        self.save_btn.clicked.connect(self.save)
        al.addWidget(self.save_btn)
        body.addWidget(actions)

        set_theme_style(self, """
            QScrollArea#companyPageScroll { background: @background@; border: 0px; }
            QWidget#companyPageViewport { background: @background@; border: 0px; }
            QWidget#companyPageContent { background: transparent; }
            QLabel#companyLogoPreview {
                background: @surface_alt@;
                border: 1px solid @border@;
                border-radius: 10px;
                color: @text_muted@;
            }
            QLabel#companyPreviewName {
                color: @text_primary@;
                background: transparent;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#companyPreviewAr {
                color: @text_secondary@;
                background: transparent;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#companyPreviewMeta {
                color: @text_muted@;
                background: transparent;
                font-size: 11px;
            }
            QLabel#companyProfileStatus {
                color: @success@;
                background: @surface_alt@;
                border: 1px solid @border@;
                border-radius: 7px;
                padding: 6px 8px;
                font-size: 11px;
                font-weight: 700;
            }
        """)


    def _add_pair(self, layout, row, col, key, label):
        label_widget = QLabel(translate_text(label))
        label_widget.setObjectName("formLabel")
        editor = QLineEdit()
        editor.setObjectName("companyField")
        editor.setMinimumHeight(32)
        editor.setMaximumHeight(35)
        editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        editor.setClearButtonEnabled(True)
        editor.textChanged.connect(self._update_preview)
        self.ed[key] = editor
        layout.addWidget(label_widget, row, col)
        layout.addWidget(editor, row, col + 1)
        layout.setColumnStretch(col + 1, 1)

    def _add_full(self, layout, row, key, label):
        label_widget = QLabel(translate_text(label))
        label_widget.setObjectName("formLabel")
        editor = QLineEdit()
        editor.setObjectName("companyField")
        editor.setMinimumHeight(32)
        editor.setMaximumHeight(35)
        editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        editor.setClearButtonEnabled(True)
        editor.textChanged.connect(self._update_preview)
        self.ed[key] = editor
        layout.addWidget(label_widget, row, 0)
        layout.addWidget(editor, row, 1, 1, 5)
        layout.setColumnStretch(1, 1)

    # ============================================================
    # Data
    # ============================================================
    def _load(self):
        conn = get_connection()
        try:
            row = conn.execute('SELECT * FROM "company info" ORDER BY id LIMIT 1').fetchone()
        finally:
            conn.close()
        for key, _ in self.FIELD_DEFINITIONS:
            if key in self.ed:
                value = row[key] if row is not None and key in row else ""
                self.ed[key].setText("" if value is None else str(value))
        self.logo_path = (row["logo path"] if row is not None and "logo path" in row else "") or ""
        self._refresh_logo()
        self._update_preview()

    def save(self):
        name = self.ed["company name"].text().strip()
        if not name:
            self.error(translate_text("Company name is required."))
            self.ed["company name"].setFocus()
            return

        conn = get_connection()
        try:
            row = conn.execute('SELECT id FROM "company info" ORDER BY id LIMIT 1').fetchone()
            keys = [key for key, _ in self.FIELD_DEFINITIONS]
            vals = [self.ed[key].text().strip() or None for key in keys]
            if "logo path" in self._company_columns(conn):
                keys.append("logo path")
                vals.append(self.logo_path or None)
            if row:
                conn.execute(
                    'UPDATE "company info" SET ' + ",".join(f'"{key}"=?' for key in keys) +
                    ',updated_at=CURRENT_TIMESTAMP WHERE id=?', vals + [row["id"]]
                )
            else:
                conn.execute(
                    'INSERT INTO "company info" (' + ",".join(f'"{key}"' for key in keys) +
                    ') VALUES (' + ",".join("?" for _ in vals) + ')', vals
                )
            conn.commit()
            window = self.window()
            refresh = getattr(window, "refresh_company_brand", None) if window else None
            if callable(refresh):
                refresh()
            self._update_preview()
            self.success(translate_text("Company profile saved successfully."))
        except (sqlite3.Error, TypeError, ValueError):
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _company_columns(conn):
        return {row["name"] for row in conn.execute('PRAGMA table_info("company info")').fetchall()}

    # ============================================================
    # Logo
    # ============================================================
    def _choose_logo(self):
        source, _ = QFileDialog.getOpenFileName(
            self,
            translate_text("Choose company logo"),
            str(ROOT_DIR),
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if not source:
            return
        destination = ROOT_DIR / "resources" / "company_logo.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(source, destination)
            self.logo_path = str(destination)
            self._refresh_logo()
            self._update_preview()
        except OSError as exc:
            self.error(f"{translate_text('Unable to save company logo.')} {exc}")

    def _reset_logo(self):
        self.logo_path = ""
        self._refresh_logo()
        self._update_preview()

    def _refresh_logo(self):
        candidates = []
        if self.logo_path:
            candidates.append(Path(self.logo_path))
        candidates.extend([
            ROOT_DIR / "resources" / "company_logo.png",
            ROOT_DIR / "resources" / "logo.png",
            ROOT_DIR / "resources" / "logo.jpg",
        ])
        self.logo.clear()
        for path in candidates:
            if path.exists():
                pix = QPixmap(str(path))
                if not pix.isNull():
                    self.logo.setPixmap(pix.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    return
        self.logo.setText("BO")

    def _update_preview(self):
        name = self.ed.get("company name")
        ar = self.ed.get("company name ar")
        activity = self.ed.get("activity")
        self.preview_name.setText((name.text().strip() if name else "") or translate_text("Company name"))
        self.preview_ar.setText(ar.text().strip() if ar else "")
        meta = (activity.text().strip() if activity else "")
        self.preview_activity.setText(meta or translate_text("Construction company profile"))

        required = ["company name", "company name ar", "owner", "address", "phone 1", "reg com", "nif", "nis"]
        completed = sum(bool(self.ed[k].text().strip()) for k in required if k in self.ed)
        total = len(required)
        if completed == total:
            status = translate_text("Profile ready: core identity and legal information are complete.")
        else:
            status = translate_text("Profile completeness") + f": {completed}/{total} " + translate_text("core fields")
        self.profile_status.setText(status)
