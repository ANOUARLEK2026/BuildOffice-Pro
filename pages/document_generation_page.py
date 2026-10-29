# ============================================================
# شرح الملف: pages/document_generation_page.py
# مركز إنشاء الوثائق في BuildOffice Pro.
# الواجهة تعرض الوثائق المطلوبة وتصنيفها وحالة القوالب فقط.
# الوثائق الرسمية التي تحتاج قوالب المستخدم تبقى مقفلة إلى أن
# يتم وضع ملفات Word/Excel النهائية داخل مجلد القوالب.
# ============================================================
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.dependency_service import (
    document_dependencies_ready,
    missing_document_dependencies,
)
from services.document_generation_service import (
    OUTPUT_DIR,
    generate_project_calendar,
    generate_text_or_csv,
)

from .base_page import BasePage


class DocumentGenerationPage(BasePage):
    """Central document catalog and generation control center.

    Official construction documents are catalogued here first. Their actual
    generation is intentionally template-gated so the user can supply the
    exact Word/Excel layouts before any production mapping is activated.
    """

    REFERENCE_DOCUMENTS: ClassVar[tuple[tuple[str, str, str], ...]] = (
        ("بيان الأشغال", "statement", "كشف الأشغال المنجزة حسب بنود الـ BOQ"),
        ("حوصلة الأشغال", "summary", "تجميع الكميات العقدية والسابقة والحالية والتراكمية"),
        ("وضعية الأشغال", "situation", "الوضعية المالية والخصومات والمبلغ الصافي للدفع"),
        ("الجرد العام والنقصان", "inventory", "مقارنة العقد والمنجز والزيادة والنقصان"),
    )

    DOCUMENT_CATALOG: ClassVar[
        tuple[tuple[str, tuple[tuple[str, str], ...]], ...]
    ] = (
        ("Quantity & BOQ", (
            ("بيان الأشغال", "Official work statement / BOQ execution statement"),
            ("حوصلة الأشغال", "Work summary by contractual and executed quantities"),
            ("الجرد العام والنقصان", "General inventory with increases and decreases"),
            ("الكشوفات التفصيلية / Attachements", "Detailed quantity measurement sheets"),
            ("الملحقات الكمية والمالية / Avenants", "Quantity and financial amendments"),
        )),
        ("Financial & Situations", (
            ("وضعية الأشغال", "Official work situation / payment statement"),
            ("Décomptes", "Progressive and final financial statements"),
            ("شهادات الدفع", "Payment certificates and supporting statements"),
            ("التسبيقات", "Advances and supply advances"),
            ("الاقتطاعات والضمان", "Retention, guarantee and deduction statements"),
            ("التقرير المالي للمشروع", "Project financial report"),
        )),
        ("Acceptance & Handover", (
            ("محضر الاستلام المؤقت", "Provisional acceptance minutes"),
            ("محضر الاستلام النهائي", "Final acceptance minutes"),
            ("محضر تسليم المشروع", "Project handover minutes"),
            ("الجرد العام ومحضر التسليم", "General inventory and handover record"),
            ("شهادات الإنجاز وحسن التنفيذ", "Completion and good-performance certificates"),
        )),
        ("Administration & Correspondence", (
            ("المراسلات الرسمية", "Official contractor/client correspondence"),
            ("الإعذارات والتنبيهات", "Notices and formal warnings"),
            ("طلبات الخدمة / أوامر الخدمة", "Service requests and orders"),
            ("شهادات التوطين والوثائق الإدارية", "Administrative and banking certificates"),
            ("محاضر الاجتماعات", "Project meeting minutes"),
        )),
        ("Staff & Payroll", (
            ("سجلات العمال", "Staff registers"),
            ("كشوف الحضور", "Attendance registers"),
            ("كشوف الرواتب", "Payroll registers"),
            ("بيانات دفع العمال", "Staff payment statements"),
            ("تقارير عمالة الموقع", "Site labor reports"),
        )),
        ("Expenses & Payments", (
            ("سندات المصاريف الشهرية", "Monthly expense vouchers"),
            ("تقارير المصاريف", "Expense reports"),
            ("سجلات المدفوعات", "Payment registers"),
            ("كشوف الموردين والديون", "Supplier and debt statements"),
        )),
        ("Planning & Control", (
            ("البرنامج الزمني للمشروع", "Project schedule"),
            ("مخططات Gantt", "Gantt schedules"),
            ("تقارير تقدم الأشغال", "Work progress reports"),
            ("تقارير مراقبة الكميات", "Quantity-control reports"),
            ("التقارير الدورية للمشروع", "Periodic project reports"),
        )),
        ("Vehicles & Equipment", (
            ("تقارير المركبات", "Vehicle reports"),
            ("سجلات المعدات", "Equipment registers"),
            ("سجلات الوقود", "Fuel registers"),
            ("تقارير الاستعمال والصيانة", "Usage and maintenance reports"),
        )),
    )

    BUILTIN_GENERATORS: ClassVar[tuple[tuple[str, str, str], ...]] = (
        ("Project financial report", "project_financial", "TXT / CSV"),
        ("Expense report", "expenses", "TXT / CSV"),
        ("Attendance report", "attendance", "TXT / CSV"),
        ("BOQ / Métré report", "boq", "TXT / CSV"),
        ("Project period calendar", "calendar", "Excel"),
    )


    def __init__(self):
        super().__init__(
            "Document Generation",
            "Central catalog for official construction documents and trusted outputs",
        )
        self._selected_reference = self.REFERENCE_DOCUMENTS[0][1]
        self._build_ui()
        self._load_projects()
        self._load_situations()
        self._update_context()

    def _label(self, text: str, muted: bool = False) -> QLabel:
        label = QLabel(translate_text(text))
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if muted:
            label.setObjectName("mutedText")
        return label

    def _make_doc_card(self, title: str, description: str, status: str = "TEMPLATE REQUIRED") -> QFrame:
        card = QFrame()
        card.setObjectName("documentCatalogCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setMinimumHeight(72)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(12)

        icon = QLabel("DOC")
        icon.setObjectName("documentCatalogIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(42, 42)
        layout.addWidget(icon)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        name = QLabel(translate_text(title))
        name.setObjectName("documentCatalogTitle")
        desc = QLabel(translate_text(description))
        desc.setObjectName("documentCatalogDescription")
        desc.setWordWrap(True)
        text_box.addWidget(name)
        text_box.addWidget(desc)
        layout.addLayout(text_box, 1)

        badge = QLabel(translate_text(status))
        badge.setObjectName("documentTemplateBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setMinimumWidth(118)
        layout.addWidget(badge)
        return card

    def _build_ui(self):
        # A dedicated scroll area prevents the long document catalog from
        # compressing combo boxes or cards when the window is resized.
        scroll = QScrollArea()
        scroll.setObjectName("documentGenerationScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("documentGenerationContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(1, 2, 8, 12)
        content_layout.setSpacing(12)
        scroll.setWidget(content)
        self.body.addWidget(scroll, 1)

        intro, il = self.panel(
            "Document Generation Center",
            "One controlled place for official construction-document outputs.",
            "@primary@",
        )
        il.addWidget(self._label(
            "Operational pages own the data and calculations. This center owns document output. "
            "Official templates supplied by the user will be connected later, without changing the data model."
        ))
        content_layout.addWidget(intro)

        # Existing internal generators remain visible and usable.
        standard, sl = self.panel(
            "Built-in reports",
            "These are the existing internal reports. They are separate from the official user-designed document templates.",
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(9)
        self.generator = QComboBox()
        self.generator.setMinimumHeight(40)
        for text, data, output in self.BUILTIN_GENERATORS:
            self.generator.addItem(translate_text(f"{text}  •  {output}"), data)
        self.generator.currentIndexChanged.connect(self._update_context)

        self.project = LocalizedComboBox()
        self.project.setMinimumHeight(40)
        self.project.currentIndexChanged.connect(self._load_situations)

        self.situation = LocalizedComboBox()
        self.situation.setMinimumHeight(40)

        self.format = QComboBox()
        self.format.setMinimumHeight(40)
        self.format.addItems(["TXT", "CSV"])

        for row, (caption, widget) in enumerate([
            ("Document type", self.generator),
            ("Project", self.project),
            ("Situation", self.situation),
            ("Report format", self.format),
        ]):
            grid.addWidget(self._label(caption), row, 0)
            grid.addWidget(widget, row, 1)
        grid.setColumnStretch(1, 1)
        sl.addLayout(grid)

        action_row = QHBoxLayout()
        self.generate_button = QPushButton(translate_text("Generate built-in report"))
        self.generate_button.setObjectName("primaryButton")
        self.generate_button.setMinimumHeight(42)
        self.generate_button.clicked.connect(self.generate)
        action_row.addWidget(self.generate_button)

        self.document_dependency_status = QLabel()
        self.document_dependency_status.setObjectName("mutedText")
        self.document_dependency_status.setWordWrap(True)
        action_row.addWidget(self.document_dependency_status, 1)
        sl.addLayout(action_row)
        content_layout.addWidget(standard)

        # Official reference families: selection only, generation locked.
        ref, rl = self.panel(
            "Official construction documents",
            "The four supplied examples are registered here. Generation stays locked until you provide the final Word/Excel templates.",
            "@primary@",
        )
        selection = QGridLayout()
        selection.setHorizontalSpacing(12)
        selection.setVerticalSpacing(9)
        self.reference_project = LocalizedComboBox()
        self.reference_project.setMinimumHeight(40)
        self.reference_project.currentIndexChanged.connect(self._load_reference_situations)
        self.reference_situation = LocalizedComboBox()
        self.reference_situation.setMinimumHeight(40)
        self.reference_output = QComboBox()
        self.reference_output.setMinimumHeight(40)
        self.reference_output.addItems(["WORD", "EXCEL", "WORD + EXCEL"])
        selection.addWidget(self._label("Project"), 0, 0)
        selection.addWidget(self.reference_project, 0, 1)
        selection.addWidget(self._label("Situation"), 1, 0)
        selection.addWidget(self.reference_situation, 1, 1)
        selection.addWidget(self._label("Output"), 2, 0)
        selection.addWidget(self.reference_output, 2, 1)
        selection.setColumnStretch(1, 1)
        rl.addLayout(selection)

        ref_grid = QGridLayout()
        ref_grid.setHorizontalSpacing(10)
        ref_grid.setVerticalSpacing(8)
        for i, (title, key, description) in enumerate(self.REFERENCE_DOCUMENTS):
            card = self._make_doc_card(title, description)
            card.mousePressEvent = lambda event, k=key: self._select_reference(k)
            ref_grid.addWidget(card, i // 2, i % 2)
        rl.addLayout(ref_grid)

        self.reference_status = self._label(
            "Selected: بيان الأشغال • Template required • Generation locked",
            muted=True,
        )
        self.reference_status.setObjectName("referenceTemplateStatus")
        rl.addWidget(self.reference_status)

        self.reference_generate = QPushButton(translate_text("Generate official document"))
        self.reference_generate.setObjectName("primaryButton")
        self.reference_generate.setMinimumHeight(42)
        self.reference_generate.setEnabled(False)
        self.reference_generate.setToolTip(translate_text("Provide the final Word/Excel template before enabling generation."))
        rl.addWidget(self.reference_generate, 0, Qt.AlignmentFlag.AlignLeft)
        content_layout.addWidget(ref)

        catalog, cl = self.panel(
            "Complete document catalog",
            "Every requested document family is registered now. Implementation is intentionally pending your templates and examples.",
        )
        catalog_grid = QGridLayout()
        catalog_grid.setHorizontalSpacing(10)
        catalog_grid.setVerticalSpacing(8)
        for i, (category, documents) in enumerate(self.DOCUMENT_CATALOG):
            group = QFrame()
            group.setObjectName("documentCategoryCard")
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(12, 10, 12, 10)
            group_layout.setSpacing(5)
            heading = QLabel(translate_text(category))
            heading.setObjectName("documentCategoryTitle")
            group_layout.addWidget(heading)
            for title, desc in documents:
                line = QLabel(f"• {translate_text(title)}")
                line.setObjectName("documentCategoryItem")
                line.setWordWrap(True)
                line.setToolTip(translate_text(desc))
                group_layout.addWidget(line)
            catalog_grid.addWidget(group, i // 2, i % 2)
        catalog_grid.setColumnStretch(0, 1)
        catalog_grid.setColumnStretch(1, 1)
        cl.addLayout(catalog_grid)
        content_layout.addWidget(catalog)

        bottom = QHBoxLayout()
        template_btn = QPushButton(translate_text("Open templates folder"))
        template_btn.setMinimumHeight(38)
        template_btn.clicked.connect(self.open_templates_folder)
        output_btn = QPushButton(translate_text("Open generated files folder"))
        output_btn.setMinimumHeight(38)
        output_btn.clicked.connect(self.open_output_folder)
        bottom.addWidget(template_btn)
        bottom.addWidget(output_btn)
        bottom.addStretch()
        content_layout.addLayout(bottom)
        content_layout.addStretch(1)

        self._load_reference_projects()
        self._refresh_dependency_state()

    def _refresh_dependency_state(self):
        missing = missing_document_dependencies()
        if missing:
            self.document_dependency_status.setText(
                translate_text(
                    "Word/Excel generation is unavailable in this Python environment. "
                    "Missing: " + ", ".join(missing) + ". Use the included dependency installer, then restart the app."
                )
            )
            self.document_dependency_status.setObjectName("warningText")
            self.document_dependency_status.style().unpolish(self.document_dependency_status)
            self.document_dependency_status.style().polish(self.document_dependency_status)
        else:
            self.document_dependency_status.setText(
                translate_text("Word/Excel dependencies: READY")
            )
            self.document_dependency_status.setObjectName("successText")
            self.document_dependency_status.style().unpolish(self.document_dependency_status)
            self.document_dependency_status.style().polish(self.document_dependency_status)

    def _load_projects(self):
        current = self.project.currentData()
        self.project.blockSignals(True)
        self.project.clear()
        self.project.addItem(translate_text("All projects"), None)
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT project_id,project_name FROM projects ORDER BY project_name"
            ).fetchall()
        finally:
            conn.close()
        for row in rows:
            self.project.addItem(f"{row['project_id']} • {row['project_name']}", row['project_id'])
        if current is not None:
            idx = self.project.findData(current)
            if idx >= 0:
                self.project.setCurrentIndex(idx)
        self.project.blockSignals(False)

    def _load_reference_projects(self):
        self.reference_project.blockSignals(True)
        self.reference_project.clear()
        self.reference_project.addItem(translate_text("Select project"), None)
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT project_id,project_name FROM projects ORDER BY project_name"
            ).fetchall()
        finally:
            conn.close()
        for row in rows:
            self.reference_project.addItem(
                f"{row['project_id']} • {row['project_name']}", row['project_id']
            )
        self.reference_project.blockSignals(False)

    def _load_situations(self):
        self.situation.blockSignals(True)
        self.situation.clear()
        self.situation.addItem(translate_text("Select a situation"), None)
        pid = self.project.currentData()
        if pid:
            conn = get_connection()
            try:
                rows = conn.execute(
                    "SELECT situation_id,situation_number,situation_date,status "
                    "FROM situations WHERE project_id=? ORDER BY situation_number DESC",
                    (pid,),
                ).fetchall()
            finally:
                conn.close()
            for row in rows:
                self.situation.addItem(
                    f"#{row['situation_number']} • {row['situation_date']} • {row['status']}",
                    row['situation_id'],
                )
        self.situation.blockSignals(False)

    def _load_reference_situations(self):
        self.reference_situation.blockSignals(True)
        self.reference_situation.clear()
        self.reference_situation.addItem(translate_text("Select a situation"), None)
        pid = self.reference_project.currentData()
        if pid:
            conn = get_connection()
            try:
                rows = conn.execute(
                    "SELECT situation_id,situation_number,situation_date,status "
                    "FROM situations WHERE project_id=? ORDER BY situation_number DESC",
                    (pid,),
                ).fetchall()
            finally:
                conn.close()
            for row in rows:
                self.reference_situation.addItem(
                    f"#{row['situation_number']} • {row['situation_date']} • {row['status']}",
                    row['situation_id'],
                )
        self.reference_situation.blockSignals(False)

    def _update_context(self):
        kind = self.generator.currentData()
        self.situation.setEnabled(kind == "situation")
        self.format.setEnabled(kind in {"project_financial", "expenses", "attendance", "boq"})

    def _select_reference(self, key: str):
        self._selected_reference = key
        names = {k: title for title, k, _ in self.REFERENCE_DOCUMENTS}
        title = names.get(key, key)
        self.reference_status.setText(
            translate_text(
                f"Selected: {title} • Template required • Generation locked until the final template is supplied"
            )
        )

    def generate(self):
        kind = self.generator.currentData()
        pid = self.project.currentData()
        try:
            if kind == "situation":
                raise RuntimeError(
                    "Project situation package generation is not available in the current document-generation service."
                )
            if kind == "calendar":
                if not document_dependencies_ready():
                    raise RuntimeError(
                        "Excel generation requires openpyxl. Run 'Install BuildOffice Pro Dependencies.bat' and restart the app."
                    )
                if not pid:
                    raise ValueError("Select a project first.")
                self.success(f"Generated file:\n{generate_project_calendar(pid)}")
                return
            self.success(
                "Generated file(s):\n"
                + "\n".join(
                    str(p) for p in generate_text_or_csv(kind, pid, self.format.currentText())
                )
            )
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            self.error(str(exc))

    def open_templates_folder(self):
        template_dir = Path(__file__).resolve().parent.parent / "resources" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(template_dir)))

    def open_output_folder(self):
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(OUTPUT_DIR))))
