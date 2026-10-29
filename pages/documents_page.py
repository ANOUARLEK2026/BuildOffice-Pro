# ============================================================
# شرح الملف: pages/documents_page.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
"""Documents library page.

The page keeps the existing company/project document tables as the data source,
but presents them as a visual library organized by the document's nature.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.document_service import (
    DOCUMENT_CATEGORIES,
    DOCUMENT_NATURES,
    NATURE_TO_CATEGORY,
    category_label,
    ensure_document_categories,
    ensure_document_schema,
    infer_nature,
)
from services.settings_service import qt_date_format

from .base_page import BasePage, SectionCard, set_button
from .id_service import next_child_id, next_sequence_id


# شرح الصنف DocumentCategoryButton: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class DocumentCategoryButton(QPushButton):
    """Compact clickable category tile for the document library."""

    def __init__(self, category: str, icon: str, description: str):
        super().__init__()
        self.category = category
        self.setObjectName("documentCategoryCard")
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(50)
        self.setMaximumHeight(56)
        self.setToolTip(translate_text(description))

        root = QHBoxLayout(self)
        root.setContentsMargins(9, 6, 9, 6)
        root.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setObjectName("documentCategoryIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(28, 28)
        root.addWidget(icon_label)

        title_label = QLabel(translate_text(category))
        title_label.setObjectName("documentCategoryTitle")
        root.addWidget(title_label, 1)

        self.count_label = QLabel("0")
        self.count_label.setObjectName("documentCategoryCount")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setMinimumWidth(22)
        root.addWidget(self.count_label)

# شرح الدالة set_count: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def set_count(self, value: int) -> None:
        self.count_label.setText(str(int(value)))


# شرح الصنف DocumentsPage: يجمع البيانات والوظائف المرتبطة بهذا المكوّن.
class DocumentsPage(BasePage):
    """Compact, scrollable visual document library."""

    SCOPE_ALL = "all"
    SCOPE_COMPANY = "company"
    SCOPE_PROJECT = "project"

    def __init__(self):
        super().__init__(
            "Documents",
            "A visual library organized by document nature and workflow",
        )
        self._selected_category = "All documents"
        self._rows: list[dict] = []
        self._category_buttons: dict[str, DocumentCategoryButton] = {}
        self._build_page()
        self.load()

# شرح الدالة _build_page: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _build_page(self) -> None:
        # Scroll only the document workspace so the page header and KPI strip remain fixed.
        scroll = QScrollArea()
        scroll.setObjectName("documentsScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.verticalScrollBar().setSingleStep(10)

        content = QWidget()
        content.setObjectName("documentsScrollContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(1, 0, 7, 3)
        
        content_layout.setSpacing(10)
        scroll.setWidget(content)
        self.body.addWidget(scroll, 1)

        toolbar = QFrame()
        toolbar.setObjectName("documentsToolbar")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(9, 6, 9, 6)
        tl.setSpacing(7)

        self.search = QLineEdit()
        self.search.setPlaceholderText(translate_text("Search by name, project or description…"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.load)

        self.scope = LocalizedComboBox()
        self.scope.addItem(translate_text("All documents"), self.SCOPE_ALL)
        self.scope.addItem(translate_text("Company documents"), self.SCOPE_COMPANY)
        self.scope.addItem(translate_text("Project documents"), self.SCOPE_PROJECT)
        self.scope.currentIndexChanged.connect(self.load)
        self.scope.setMinimumWidth(160)

        add_company = QPushButton(translate_text("+ Company"))
        set_button(add_company, "secondary")
        add_company.clicked.connect(lambda: self.dialog(True))

        add_project = QPushButton(translate_text("+ Project"))
        set_button(add_project, "primary")
        add_project.clicked.connect(lambda: self.dialog(False))

        refresh = QPushButton(translate_text("↻"))
        set_button(refresh, "secondary")
        refresh.setFixedWidth(38)
        refresh.setToolTip(translate_text("Refresh this page from the database"))
        refresh.clicked.connect(self.load)

        tl.addWidget(self.search, 1)
        tl.addWidget(self.scope)
        tl.addWidget(add_company)
        tl.addWidget(add_project)
        tl.addWidget(refresh)
        content_layout.addWidget(toolbar)

        categories_card = SectionCard(
            translate_text("Document library"),
            translate_text("Choose a document nature to filter the workspace."),
            "@primary@",
        )
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(7)
        grid.setVerticalSpacing(7)
        for column in range(4):
            grid.setColumnStretch(column, 1)

        all_button = DocumentCategoryButton(
            "All documents", "▦", "Browse the complete document registry"
        )
        self._category_buttons["All documents"] = all_button
        all_button.clicked.connect(lambda _checked=False: self._select_category("All documents"))
        grid.addWidget(all_button, 0, 0)

        for index, (category, icon, description) in enumerate(DOCUMENT_CATEGORIES, start=1):
            button = DocumentCategoryButton(category, icon, description)
            self._category_buttons[category] = button
            button.clicked.connect(lambda _checked=False, value=category: self._select_category(value))
            row, col = divmod(index, 4)
            grid.addWidget(button, row, col)

        categories_card.add_layout(grid)
        content_layout.addWidget(categories_card)

        workspace = SectionCard(
            translate_text("Document workspace"),
            translate_text("Select a document to open, edit or remove its registry record."),
            "@info@",
        )
        actions = QHBoxLayout()
        self.current_category_label = QLabel(translate_text("All documents"))
        self.current_category_label.setObjectName("sectionTitle")
        actions.addWidget(self.current_category_label)
        actions.addStretch()

        self.open_button = QPushButton(translate_text("Open"))
        set_button(self.open_button, "gold")
        self.open_button.clicked.connect(self._open_selected)
        self.edit_button = QPushButton(translate_text("Edit"))
        set_button(self.edit_button, "secondary")
        self.edit_button.clicked.connect(self._edit_selected)
        self.delete_button = QPushButton(translate_text("Delete"))
        set_button(self.delete_button, "danger")
        self.delete_button.clicked.connect(self._delete_selected)
        actions.addWidget(self.open_button)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.delete_button)
        workspace.add_layout(actions)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            translate_text("Document"),
            translate_text("Nature"),
            translate_text("Scope"),
            translate_text("Project"),
            translate_text("Date"),
            translate_text("Expiry"),
            translate_text("Status"),
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(220)
        self.table.setMaximumHeight(355)
        self.table.doubleClicked.connect(lambda *_args: self._open_selected())
        workspace.add(self.table)
        content_layout.addWidget(workspace)
        content_layout.addStretch(1)

        self._select_category("All documents")

# شرح الدالة _select_category: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _select_category(self, category: str) -> None:
        self._selected_category = category
        self.current_category_label.setText(translate_text(category))
        for key, button in self._category_buttons.items():
            button.setProperty("selected", key == category)
            button.style().unpolish(button)
            button.style().polish(button)
        self.load()

# شرح الدالة _current_scope: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _current_scope(self) -> str:
        return str(self.scope.currentData() or self.SCOPE_ALL)

# شرح الدالة load: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def load(self, *_args) -> None:
        conn = get_connection()
        try:
            # Existing records are preserved. Only empty category fields are filled.
            try:
                conn.execute("BEGIN IMMEDIATE")
                ensure_document_categories(conn)
                conn.commit()
            except sqlite3.Error:
                conn.rollback()

            rows: list[dict] = []
            scope = self._current_scope()
            query = self.search.text().strip().casefold()
            selected_category = self._selected_category

            if scope in (self.SCOPE_ALL, self.SCOPE_COMPANY):
                company_rows = conn.execute(
                    '''
                    SELECT document_id, "document name", "document path",
                           "upload date", "expiring date", description, status,
                           category
                    FROM "company documents"
                    ORDER BY "upload date" DESC, document_id DESC
                    '''
                ).fetchall()
                for row in company_rows:
                    rows.append(self._normalize(row, True))

            if scope in (self.SCOPE_ALL, self.SCOPE_PROJECT):
                project_rows = conn.execute(
                    '''
                    SELECT d.item_id, d.project_id, d.document_name,
                           d.document_path, d.upload_date, d.expiring_date,
                           d.description, d.status, d.category, d.related_entity,
                           p.project_name
                    FROM "projects documents" d
                    LEFT JOIN projects p ON p.project_id=d.project_id
                    ORDER BY d.upload_date DESC, d.item_id DESC
                    '''
                ).fetchall()
                for row in project_rows:
                    rows.append(self._normalize(row, False))

            filtered = []
            for row in rows:
                if selected_category != "All documents" and row["category"] != selected_category:
                    continue
                haystack = " ".join(
                    str(row.get(key) or "")
                    for key in ("name", "project_name", "description", "category", "status")
                ).casefold()
                if query and query not in haystack:
                    continue
                filtered.append(row)

            self._rows = filtered
            self._fill_table(filtered)
            self._update_counts(conn)
        finally:
            conn.close()

# شرح الدالة _normalize: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    @staticmethod
    def _normalize(row, company: bool) -> dict:
        if company:
            return {
                "id": str(row["document_id"]),
                "name": str(row["document name"] or ""),
                "path": str(row["document path"] or ""),
                "upload_date": row["upload date"],
                "expiry": row["expiring date"],
                "description": row["description"] or "",
                "status": row["status"] or "Active",
                "category": category_label(row["category"]),
                "company": True,
                "project_id": None,
                "project_name": "Company",
                "related_entity": None,
            }
        return {
            "id": str(row["item_id"]),
            "name": str(row["document_name"] or ""),
            "path": str(row["document_path"] or ""),
            "upload_date": row["upload_date"],
            "expiry": row["expiring_date"],
            "description": row["description"] or "",
            "status": row["status"] or "Active",
            "category": category_label(row["category"]),
            "company": False,
            "project_id": row["project_id"],
            "project_name": row["project_name"] or "No project",
            "related_entity": row["related_entity"],
        }

# شرح الدالة _update_counts: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _update_counts(self, conn) -> None:
        counts = {key: 0 for key, _icon, _desc in DOCUMENT_CATEGORIES}
        counts["All documents"] = 0
        scope = self._current_scope()

        statements = []
        if scope in (self.SCOPE_ALL, self.SCOPE_COMPANY):
            statements.append('SELECT category, COUNT(*) AS n FROM "company documents" GROUP BY category')
        if scope in (self.SCOPE_ALL, self.SCOPE_PROJECT):
            statements.append('SELECT category, COUNT(*) AS n FROM "projects documents" GROUP BY category')

        for sql in statements:
            for row in conn.execute(sql).fetchall():
                category = category_label(row["category"])
                if category not in counts:
                    category = "Other"
                counts[category] += int(row["n"] or 0)
                counts["All documents"] += int(row["n"] or 0)

        for key, button in self._category_buttons.items():
            button.set_count(counts.get(key, 0))

# شرح الدالة _fill_table: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _fill_table(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (
                row["name"],
                translate_text(row["category"]),
                translate_text("Company") if row["company"] else translate_text("Project"),
                row["project_name"],
                str(row["upload_date"] or "")[:10],
                str(row["expiry"] or ""),
                translate_text(row["status"]),
            )
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                self.table.setItem(row_index, col_index, item)
        self.table.setSortingEnabled(False)

# شرح الدالة _selected_row: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _selected_row(self) -> dict | None:
        row_index = self.table.currentRow()
        if row_index < 0 or row_index >= len(self._rows):
            return None
        return self._rows[row_index]

# شرح الدالة _edit_selected: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _edit_selected(self) -> None:
        row = self._selected_row()
        if not row:
            self.error(translate_text("Select a document first."))
            return
        self.dialog(row["company"], row["id"])

# شرح الدالة _open_selected: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _open_selected(self) -> None:
        row = self._selected_row()
        if not row:
            self.error(translate_text("Select a document first."))
            return
        path = Path(row["path"])
        if not row["path"] or not path.exists():
            self.error(translate_text("The physical file could not be found at the stored path."))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))

# شرح الدالة _delete_selected: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def _delete_selected(self) -> None:
        row = self._selected_row()
        if not row:
            self.error(translate_text("Select a document first."))
            return
        if not self.confirm(
            translate_text(
                "Delete this document record? The physical file will not be deleted."
            ),
            translate_text("Delete document"),
        ):
            return

        conn = get_connection()
        try:
            if row["company"]:
                conn.execute('DELETE FROM "company documents" WHERE document_id=?', (row["id"],))
            else:
                conn.execute('DELETE FROM "projects documents" WHERE item_id=?', (row["id"],))
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            self.error(translate_text(f"Could not delete the document.\n\n{exc}"))
            return
        finally:
            conn.close()
        self.load()

# شرح الدالة dialog: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
    def dialog(self, company: bool, doc_id: str | None = None) -> None:
        """Show a scope-aware editor whose fields change with document nature."""
        conn = get_connection()
        existing = None
        projects = []
        try:
            ensure_document_schema(conn)
            conn.commit()
            if doc_id:
                table = "company documents" if company else "projects documents"
                id_column = "document_id" if company else "item_id"
                existing = conn.execute(
                    f'SELECT * FROM "{table}" WHERE {id_column}=?', (doc_id,)
                ).fetchone()
            projects = conn.execute(
                "SELECT project_id, project_name FROM projects ORDER BY project_name"
            ).fetchall()
        finally:
            conn.close()

        dlg = QDialog(self)
        dlg.setWindowTitle(translate_text("Edit document") if existing else translate_text("Add document"))
        dlg.resize(760, 650)

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.verticalScrollBar().setSingleStep(20)
        outer.addWidget(scroll, 1)

        content = QWidget()
        form = QFormLayout(content)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        scroll.setWidget(content)

        name = QLineEdit()
        path = QLineEdit()
        browse = QPushButton(translate_text("Browse…"))
        browse.clicked.connect(lambda: path.setText(QFileDialog.getOpenFileName(dlg, translate_text("Select document"))[0] or path.text()))
        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.addWidget(path, 1)
        path_row.addWidget(browse)
        path_widget = QWidget()
        path_widget.setLayout(path_row)

        project = LocalizedComboBox()
        project.addItem(translate_text("No project"), None)
        for project_row in projects:
            project.addItem(project_row["project_name"], project_row["project_id"])

        nature = LocalizedComboBox()
        nature_key = "company" if company else "project"
        for key, icon in DOCUMENT_NATURES[nature_key]:
            nature.addItem(f"{icon}  {translate_text(key)}", key)

        reference = QLineEdit()
        issue_date = QDateEdit(QDate.currentDate())
        issue_date.setCalendarPopup(True)
        issue_date.setDisplayFormat(qt_date_format())

        expiry = QDateEdit(QDate.currentDate())
        expiry.setCalendarPopup(True)
        expiry.setDisplayFormat(qt_date_format())
        no_expiry = QPushButton(translate_text("No expiry"))
        no_expiry.setCheckable(True)
        no_expiry.setChecked(True)
        expiry_row = QHBoxLayout()
        expiry_row.setContentsMargins(0, 0, 0, 0)
        expiry_row.addWidget(expiry)
        expiry_row.addWidget(no_expiry)
        expiry_widget = QWidget()
        expiry_widget.setLayout(expiry_row)

        reminder = QLineEdit("30")
        reminder.setPlaceholderText("30")
        status = LocalizedComboBox()
        for key in ("Active", "Expired", "Archived"):
            status.addItem(translate_text(key), key)
        description = QLineEdit()

        if not company:
            form.addRow(translate_text("Project"), project)
        form.addRow(translate_text("Document name"), name)
        form.addRow(translate_text("Document path"), path_widget)
        form.addRow(translate_text("Nature"), nature)
        form.addRow(translate_text("Reference number"), reference)
        form.addRow(translate_text("Issue date"), issue_date)
        form.addRow(translate_text("Expiry date"), expiry_widget)
        form.addRow(translate_text("Reminder days"), reminder)
        form.addRow(translate_text("Status"), status)
        form.addRow(translate_text("Description"), description)

        properties_frame = QFrame()
        properties_frame.setObjectName("documentPropertiesFrame")
        properties_layout = QFormLayout(properties_frame)
        properties_layout.setContentsMargins(10, 10, 10, 10)
        properties_layout.setVerticalSpacing(7)
        properties_title = QLabel(translate_text("Nature-specific properties"))
        properties_title.setObjectName("sectionTitle")
        form.addRow(properties_title, properties_frame)
        property_widgets: dict[str, QWidget] = {}

# شرح الدالة add_prop: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
        def add_prop(key: str, label: str, widget: QWidget):
            property_widgets[key] = widget
            properties_layout.addRow(translate_text(label), widget)

# شرح الدالة build_properties: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
        def build_properties(kind: str):
            while properties_layout.rowCount():
                properties_layout.removeRow(0)
            property_widgets.clear()
            if kind == "Staff":
                for key, label in (("staff_name", "Employee name"), ("staff_role", "Position / role"), ("staff_id", "Staff ID"), ("staff_start", "Employment start"), ("staff_end", "Employment end")):
                    add_prop(key, label, QLineEdit())
            elif kind == "Invoice":
                add_prop("supplier", "Supplier", QLineEdit())
                add_prop("invoice_no", "Invoice number", QLineEdit())
                add_prop("amount", "Amount", QLineEdit())
                add_prop("currency", "Currency", QLineEdit("DZD"))
                add_prop("due_date", "Due date", QLineEdit())
                cb = QComboBox()
                cb.addItem(translate_text("Unpaid"), "Unpaid")
                cb.addItem(translate_text("Partially paid"), "Partially paid")
                cb.addItem(translate_text("Paid"), "Paid")
                add_prop("payment_status", "Payment status", cb)
            elif kind == "Renting":
                for key, label in (("landlord", "Landlord"), ("asset", "Rented asset / premises"), ("start_date", "Rental start"), ("end_date", "Rental end"), ("monthly_rent", "Monthly rent"), ("deposit", "Deposit")):
                    add_prop(key, label, QLineEdit())
            elif kind == "Legal":
                for key, label in (("authority", "Authority / body"), ("case_no", "Reference / case number"), ("lawyer", "Lawyer / representative"), ("legal_date", "Relevant date"), ("subject", "Subject")):
                    add_prop(key, label, QLineEdit())
            elif kind == "Tax":
                for key, label in (("tax_type", "Tax type"), ("period", "Tax period"), ("declaration_no", "Declaration number"), ("deadline", "Deadline"), ("amount", "Amount")):
                    add_prop(key, label, QLineEdit())
            elif kind == "Insurance":
                for key, label in (("insurer", "Insurer"), ("policy_no", "Policy number"), ("insured_asset", "Insured asset"), ("coverage", "Coverage"), ("premium", "Premium")):
                    add_prop(key, label, QLineEdit())
            elif kind == "Certificate":
                for key, label in (("issuer", "Issuer"), ("certificate_no", "Certificate number"), ("holder", "Holder"), ("certificate_type", "Certificate type")):
                    add_prop(key, label, QLineEdit())
            elif kind in ("Company Contract", "Contract"):
                for key, label in (("party_a", "First party"), ("party_b", "Second party"), ("contract_no", "Contract number"), ("contract_value", "Contract value"), ("start_date", "Start date"), ("end_date", "End date")):
                    add_prop(key, label, QLineEdit())
            elif kind == "Situation":
                linked = QComboBox()
                linked.addItem(translate_text("None"), None)
                c2 = None
                try:
                    c2 = get_connection()
                    selected_project = project.currentData()
                    if selected_project:
                        rows = c2.execute(
                            "SELECT situation_id, situation_number FROM situations WHERE project_id=? ORDER BY situation_number DESC",
                            (selected_project,),
                        ).fetchall()
                    else:
                        rows = c2.execute(
                            "SELECT situation_id, situation_number FROM situations ORDER BY situation_number DESC"
                        ).fetchall()
                    for r in rows:
                        linked.addItem(str(r["situation_number"]), r["situation_id"])
                finally:
                    if c2 is not None:
                        c2.close()
                add_prop("situation_id", "Linked situation", linked)
                for key, label in (("period", "Period"), ("executed_amount", "Executed amount"), ("progress", "Progress %")):
                    add_prop(key, label, QLineEdit())
            elif kind == "Request":
                for key, label in (("requested_to", "Requested from / to"), ("request_type", "Request type"), ("response_deadline", "Response deadline"), ("request_status", "Request status")):
                    add_prop(key, label, QLineEdit())
            elif kind == "Payment":
                for key, label in (("payee", "Payee"), ("amount", "Amount"), ("payment_date", "Payment date"), ("payment_method", "Payment method"), ("payment_reference", "Payment reference")):
                    add_prop(key, label, QLineEdit())
            elif kind == "BOQ / Métré":
                for key, label in (("revision", "Revision"), ("contract_no", "Contract number"), ("total_value", "Total value")):
                    add_prop(key, label, QLineEdit())
            elif kind == "Technical":
                for key, label in (("discipline", "Discipline"), ("revision", "Revision"), ("prepared_by", "Prepared by"), ("approved_by", "Approved by")):
                    add_prop(key, label, QLineEdit())
            else:
                for key, label in (("sender", "Sender"), ("recipient", "Recipient"), ("reference", "External reference"), ("subject", "Subject")):
                    add_prop(key, label, QLineEdit())

# شرح الدالة toggle_expiry: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
        def toggle_expiry():
            expiry.setEnabled(not no_expiry.isChecked())

        nature.currentIndexChanged.connect(lambda _i: build_properties(str(nature.currentData() or "Other")))
        project.currentIndexChanged.connect(lambda _i: build_properties("Situation") if nature.currentData() == "Situation" else None)
        no_expiry.toggled.connect(toggle_expiry)
        build_properties(str(nature.currentData() or "Other"))

        if existing:
            if company:
                name.setText(existing["document name"] or "")
                path.setText(existing["document path"] or "")
                expiry_value = existing["expiring date"] or ""
                category_value = existing["category"] or "Other"
                project_value = None
            else:
                name.setText(existing["document_name"] or "")
                path.setText(existing["document_path"] or "")
                expiry_value = existing["expiring_date"] or ""
                category_value = existing["category"] or "Other"
                project_value = existing["project_id"]
                idx = project.findData(project_value)
                if idx >= 0: project.setCurrentIndex(idx)
            description.setText(existing["description"] or "")
            reference.setText(existing["reference_no"] or "")
            status_idx = status.findData(existing["status"] or "Active")
            if status_idx >= 0: status.setCurrentIndex(status_idx)
            issue_value = existing["issue_date"] or ""
            if issue_value:
                dv = QDate.fromString(str(issue_value)[:10], "yyyy-MM-dd")
                if dv.isValid(): issue_date.setDate(dv)
            if expiry_value:
                no_expiry.setChecked(False)
                dv = QDate.fromString(str(expiry_value)[:10], "yyyy-MM-dd")
                if dv.isValid(): expiry.setDate(dv)
            else:
                no_expiry.setChecked(True)
            reminder.setText(str(existing["reminder_days"] or 30))
            nature_value = existing["nature"] or infer_nature(nature_key, name.text(), description.text(), category_value)
            idx = nature.findData(nature_value)
            if idx >= 0: nature.setCurrentIndex(idx)
            try:
                metadata = json.loads(existing["metadata_json"] or "{}")
            except (TypeError, ValueError):
                metadata = {}
            for key, value in metadata.items():
                widget = property_widgets.get(key)
                if isinstance(widget, QLineEdit): widget.setText(str(value or ""))
                elif isinstance(widget, QComboBox):
                    idx = widget.findData(value)
                    if idx >= 0: widget.setCurrentIndex(idx)
                    else: widget.setCurrentText(str(value))
        toggle_expiry()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        outer.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        document_name = name.text().strip()
        document_path = path.text().strip()
        if not document_name or not document_path:
            self.error(translate_text("Document name and path are required."))
            return
        try:
            reminder_value = max(0, int(reminder.text().strip() or "30"))
        except ValueError:
            self.error(translate_text("Reminder days must be a whole number."))
            return

        nature_value = str(nature.currentData() or "Other")
        category_value = NATURE_TO_CATEGORY.get(nature_value, "Other")
        status_value = str(status.currentData() or "Active")
        expiry_value = None if no_expiry.isChecked() else expiry.date().toString("yyyy-MM-dd")
        issue_value = issue_date.date().toString("yyyy-MM-dd")
        metadata = {}
        for key, widget in property_widgets.items():
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
                if value: metadata[key] = value
            elif isinstance(widget, QComboBox):
                value = widget.currentData()
                if value is not None: metadata[key] = value
        metadata_json = json.dumps(metadata, ensure_ascii=False)

        conn = get_connection()
        try:
            ensure_document_schema(conn)
            if company:
                if existing:
                    conn.execute('''
                        UPDATE "company documents"
                        SET "document name"=?, "document path"=?, "expiring date"=?, description=?,
                            status=?, category=?, nature=?, reference_no=?, issue_date=?, reminder_days=?, metadata_json=?
                        WHERE document_id=?
                    ''', (document_name, document_path, expiry_value, description.text().strip(), status_value,
                          category_value, nature_value, reference.text().strip(), issue_value, reminder_value, metadata_json, doc_id))
                else:
                    new_id = next_sequence_id(conn, "doc-gen", digits=3)
                    conn.execute('''
                        INSERT INTO "company documents"(
                            document_id, "document name", "document path", "expiring date", description,
                            status, category, nature, reference_no, issue_date, reminder_days, metadata_json
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    ''', (new_id, document_name, document_path, expiry_value, description.text().strip(), status_value,
                          category_value, nature_value, reference.text().strip(), issue_value, reminder_value, metadata_json))
            else:
                project_id = project.currentData()
                if not project_id:
                    self.error(translate_text("Select a project."))
                    return
                if existing:
                    conn.execute('''
                        UPDATE "projects documents"
                        SET project_id=?, document_name=?, document_path=?, expiring_date=?, description=?,
                            status=?, category=?, nature=?, reference_no=?, issue_date=?, reminder_days=?, metadata_json=?
                        WHERE item_id=?
                    ''', (project_id, document_name, document_path, expiry_value, description.text().strip(), status_value,
                          category_value, nature_value, reference.text().strip(), issue_value, reminder_value, metadata_json, doc_id))
                else:
                    new_id = next_child_id(conn, "doc", project_id, digits=3)
                    conn.execute('''
                        INSERT INTO "projects documents"(
                            item_id, project_id, document_name, document_path, expiring_date, description,
                            status, category, nature, reference_no, issue_date, reminder_days, metadata_json
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ''', (new_id, project_id, document_name, document_path, expiry_value, description.text().strip(),
                          status_value, category_value, nature_value, reference.text().strip(), issue_value, reminder_value, metadata_json))
            conn.commit()
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            self.error(translate_text(f"Could not save document.\n\n{exc}"))
            return
        finally:
            conn.close()
        self.load()
