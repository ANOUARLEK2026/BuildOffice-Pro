# ============================================================
# شرح الملف: attendance_page.py
# يحتوي هذا الملف على جزء من وظائف وتفاصيل تطبيق BuildOffice Pro.
# التعليقات العربية هنا للتوضيح فقط ولا تغيّر منطق البرنامج.
# ============================================================
import sqlite3

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.i18n import LocalizedComboBox, translate_text
from repositories.db import get_connection
from services.settings_service import qt_date_format

from .base_page import BasePage
from .id_service import next_child_id


# هذا الصنف مسؤول عن جزء AttendanceDialog من التطبيق.
class AttendanceDialog(QDialog):
    """Dialog used to create or edit one attendance record."""

    # تهيئة الكائن وتجهيز الواجهة والبيانات اللازمة.
    def __init__(
        self,
        worker_name,
        project_name,
        date_text,
        existing=None,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(translate_text("Attendance Details"))
        self.setMinimumWidth(420)

        layout = QFormLayout(self)

        self.worker_label = QLabel(worker_name)
        self.project_label = QLabel(project_name)
        self.date_label = QLabel(date_text)

        self.status = LocalizedComboBox()
        self.status.addItems(
            [
                translate_text("Present"),
                translate_text("Absent"),
                translate_text("Leave"),
                translate_text("Sick"),
                translate_text("Holiday"),
            ]
        )

        self.hours = QDoubleSpinBox()
        self.hours.setRange(0, 24)
        self.hours.setDecimals(2)
        self.hours.setValue(8)

        self.overtime = QDoubleSpinBox()
        self.overtime.setRange(0, 24)
        self.overtime.setDecimals(2)

        self.notes = QLineEdit()
        self.notes.setPlaceholderText(translate_text("Notes"))

        layout.addRow(translate_text("Worker:"), self.worker_label)
        layout.addRow(translate_text("Project:"), self.project_label)
        layout.addRow(translate_text("Date:"), self.date_label)
        layout.addRow(translate_text("Status:"), self.status)
        layout.addRow(translate_text("Working hours:"), self.hours)
        layout.addRow(translate_text("Overtime:"), self.overtime)
        layout.addRow(translate_text("Notes:"), self.notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if existing:
            self.status.setCurrentText(existing["status"] or "Present")
            self.hours.setValue(float(existing["working_hours"] or 0))
            self.overtime.setValue(float(existing["overtime_hours"] or 0))
            self.notes.setText(existing["notes"] or "")


# هذا الصنف مسؤول عن جزء AttendancePage من التطبيق.
class AttendancePage(BasePage):
    # تهيئة الكائن وتجهيز الواجهة والبيانات اللازمة.
    def __init__(self):
        super().__init__("Attendance", "Monthly attendance management")

        self.workers = []
        self.build_ui()
        self.load_projects()
        self.load_grid()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    # بناء عناصر واجهة المستخدم وترتيبها.

    def build_ui(self):
        controls = QGridLayout()

        # ==========================================================
        # Filters and actions
        # ==========================================================

        self.view_type = LocalizedComboBox()
        self.view_type.addItems(
            [
                translate_text("On Site"),
                translate_text("Administration"),
                translate_text("Other"),
            ]
        )
        self.view_type.currentIndexChanged.connect(self.view_type_changed)

        self.project = LocalizedComboBox()
        self.project.currentIndexChanged.connect(self.load_grid)

        self.month = LocalizedComboBox()
        self.month.addItems(
            [
                translate_text("January"),
                translate_text("February"),
                translate_text("March"),
                translate_text("April"),
                translate_text("May"),
                translate_text("June"),
                translate_text("July"),
                translate_text("August"),
                translate_text("September"),
                translate_text("October"),
                translate_text("November"),
                translate_text("December"),
            ]
        )
        self.month.setCurrentIndex(QDate.currentDate().month() - 1)
        self.month.currentIndexChanged.connect(self.load_grid)

        self.year = QSpinBox()
        self.year.setRange(2020, 2100)
        self.year.setValue(QDate.currentDate().year())
        self.year.valueChanged.connect(self.load_grid)

        refresh = QPushButton(translate_text("Refresh"))
        refresh.clicked.connect(self.refresh_all)

        save = QPushButton(translate_text("Save"))
        save.setObjectName("primaryButton")
        save.clicked.connect(self.save_all)

        clear = QPushButton(translate_text("Clear Month"))
        clear.clicked.connect(self.clear_month)

        # Filter labels
        controls.addWidget(
            QLabel(translate_text("View:")),
            0,
            0,
        )
        controls.addWidget(
            self.view_type,
            0,
            1,
        )

        controls.addWidget(
            QLabel(translate_text("Project:")),
            0,
            2,
        )
        controls.addWidget(
            self.project,
            0,
            3,
        )

        controls.addWidget(
            QLabel(translate_text("Month:")),
            0,
            4,
        )
        controls.addWidget(
            self.month,
            0,
            5,
        )

        controls.addWidget(
            QLabel(translate_text("Year:")),
            0,
            6,
        )
        controls.addWidget(
            self.year,
            0,
            7,
        )

        # Actions
        controls.addWidget(
            save,
            0,
            8,
        )
        controls.addWidget(
            refresh,
            0,
            9,
        )
        controls.addWidget(
            clear,
            0,
            10,
        )

        self.body.addLayout(controls)

        # ==========================================================
        # Attendance grid
        # ==========================================================

        # Create the container explicitly instead of using self.panel().
        frame = QFrame()
        frame.setObjectName("sectionCard")

        table_layout = QVBoxLayout(frame)
        table_layout.setContentsMargins(16, 16, 16, 16)
        table_layout.setSpacing(10)

        self.table = QTableWidget()
        self.table.setProperty("bo_auto_fit", False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.cellClicked.connect(self.cell_clicked)

        table_layout.addWidget(self.table)

        self.body.addWidget(frame)

        # ==========================================================
        # Statistics
        # ==========================================================

        stats_box = QGroupBox(translate_text("Attendance Statistics"))

        stats_layout = QGridLayout(stats_box)

        self.total_workers = QLabel("0")
        self.present_count = QLabel("0")
        self.absent_count = QLabel("0")
        self.leave_count = QLabel("0")
        self.sick_count = QLabel("0")
        self.total_hours = QLabel("0.00")
        self.total_overtime = QLabel("0.00")
        self.best_attendance = QLabel("-")
        self.most_absent = QLabel("-")
        self.most_hours = QLabel("-")

        stat_items = [
            ("Workers", self.total_workers),
            ("Present days", self.present_count),
            ("Absent days", self.absent_count),
            ("Leave days", self.leave_count),
            ("Sick days", self.sick_count),
            ("Working hours", self.total_hours),
            ("Overtime hours", self.total_overtime),
            ("Highest attendance", self.best_attendance),
            ("Most absent", self.most_absent),
            ("Most hours", self.most_hours),
        ]

        for index, (label, value) in enumerate(stat_items):
            row = index // 5
            col = (index % 5) * 2

            stats_layout.addWidget(
                QLabel(translate_text(label) + ":"),
                row,
                col,
            )

            stats_layout.addWidget(
                value,
                row,
                col + 1,
            )

        self.body.addWidget(stats_box)

        # ------------------------------------------------------------------
        # View / project handling
        # ------------------------------------------------------------------

        # تنفيذ وظيفة view_type_changed ضمن هذا الجزء من البرنامج.

    def view_type_changed(self):
        needs_project = self.view_type.currentText() != "Administration"
        self.project.setEnabled(needs_project)
        self.load_grid()

    # تنفيذ وظيفة load_projects ضمن هذا الجزء من البرنامج.
    def load_projects(self):
        conn = get_connection()
        try:
            self.project.blockSignals(True)
            self.project.clear()

            rows = conn.execute("""
                SELECT project_id, project_name
                FROM projects
                WHERE status = 'Active'
                ORDER BY project_name
            """).fetchall()

            for row in rows:
                self.project.addItem(row["project_name"], row["project_id"])
        finally:
            self.project.blockSignals(False)
            conn.close()

            self.project.setEnabled(self.view_type.currentText() != "Administration")

    # تحديث العناصر أو البيانات المعروضة في الواجهة.
    def refresh_all(self):
        current_project = self.project.currentData()
        self.load_projects()

        if current_project is not None:
            index = self.project.findData(current_project)
            if index >= 0:
                self.project.setCurrentIndex(index)

        self.load_grid()

    # ------------------------------------------------------------------
    # Workers
    # ------------------------------------------------------------------

    # تنفيذ وظيفة load_workers ضمن هذا الجزء من البرنامج.
    def load_workers(self):
        conn = get_connection()
        try:
            view_type = self.view_type.currentText()
            if view_type == "Administration":
                return conn.execute("""
                    SELECT staff_id, full_name, attendance_type
                    FROM staff
                    WHERE status = 'Active'
                      AND attendance_type = 'Administration'
                    ORDER BY full_name
                """).fetchall()

            project_id = self.project.currentData()
            if not project_id:
                return []

            # On Site and Other workers are project-based. Their assignments
            # are stored in staff_projects, while attendance_type remains
            # exactly "On Site" or "Other" in the staff table.
            return conn.execute(
                """
                SELECT s.staff_id, s.full_name, s.attendance_type
                FROM staff s
                JOIN staff_projects sp ON sp.staff_id = s.staff_id
                WHERE sp.project_id = ?
                  AND sp.active = 1
                  AND s.status = 'Active'
                  AND s.attendance_type = ?
                ORDER BY s.full_name
            """,
                (project_id, view_type),
            ).fetchall()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Grid
    # ------------------------------------------------------------------

    # تنفيذ وظيفة days_in_selected_month ضمن هذا الجزء من البرنامج.
    def days_in_selected_month(self):
        year = self.year.value()
        month = self.month.currentIndex() + 1
        return QDate(year, month, 1).daysInMonth()

    # تنفيذ وظيفة load_grid ضمن هذا الجزء من البرنامج.
    def load_grid(self):
        self.workers = self.load_workers()

        days = self.days_in_selected_month()

        self.table.blockSignals(True)
        self.table.clear()
        self.table.setRowCount(len(self.workers))
        self.table.setColumnCount(days + 1)

        self.table.setHorizontalHeaderItem(0, QTableWidgetItem("Worker"))

        for day in range(1, days + 1):
            self.table.setHorizontalHeaderItem(day, QTableWidgetItem(str(day)))

        for row, worker in enumerate(self.workers):
            item = QTableWidgetItem(worker["full_name"])
            item.setData(Qt.ItemDataRole.UserRole, worker["staff_id"])
            self.table.setItem(row, 0, item)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        for col in range(1, days + 1):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, 42)

        self.load_attendance()

        self.table.blockSignals(False)
        self.update_statistics()

    # تنفيذ وظيفة status_symbol ضمن هذا الجزء من البرنامج.
    def status_symbol(self, status):
        return {
            "Present": "✓",
            "Absent": "A",
            "Leave": "L",
            "Sick": "S",
            "Holiday": "H",
        }.get(status, "")

    # تنفيذ وظيفة load_attendance ضمن هذا الجزء من البرنامج.
    def load_attendance(self):
        if not self.workers:
            return

        year = self.year.value()
        month = self.month.currentIndex() + 1
        last_day = self.days_in_selected_month()

        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"

        conn = get_connection()

        try:
            if self.view_type.currentText() == "Administration":
                rows = conn.execute(
                    """
                    SELECT
                        staff_id,
                        date,
                        working_hours,
                        overtime_hours,
                        status,
                        notes
                    FROM attendance
                    WHERE project_id IS NULL
                      AND date BETWEEN ? AND ?
                """,
                    (start_date, end_date),
                ).fetchall()
            else:
                project_id = self.project.currentData()

                if not project_id:
                    return

                rows = conn.execute(
                    """
                    SELECT
                        staff_id,
                        date,
                        working_hours,
                        overtime_hours,
                        status,
                        notes
                    FROM attendance
                    WHERE project_id = ?
                      AND date BETWEEN ? AND ?
                """,
                    (project_id, start_date, end_date),
                ).fetchall()

            worker_rows = {
                worker["staff_id"]: index for index, worker in enumerate(self.workers)
            }

            for record in rows:
                staff_id = record["staff_id"]

                if staff_id not in worker_rows:
                    continue

                day = int(record["date"].split("-")[2])
                row = worker_rows[staff_id]

                item = QTableWidgetItem(self.status_symbol(record["status"]))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setData(Qt.ItemDataRole.UserRole, dict(record))

                self.table.setItem(row, day, item)

        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Cell dialog
    # ------------------------------------------------------------------

    # تنفيذ وظيفة cell_clicked ضمن هذا الجزء من البرنامج.
    def cell_clicked(self, row, column):
        if column == 0 or row >= len(self.workers):
            return

        worker = self.workers[row]

        year = self.year.value()
        month = self.month.currentIndex() + 1
        day = column

        date = QDate(year, month, day)

        if not date.isValid():
            return

        existing = None
        item = self.table.item(row, column)

        if item:
            existing = item.data(Qt.ItemDataRole.UserRole)

        if self.view_type.currentText() == "Administration":
            project_id = None
            project_name = "Administration / No project"
        else:
            project_id = self.project.currentData()

            if not project_id:
                self.error("Select a project first.")
                return

            project_name = self.project.currentText()

        dialog = AttendanceDialog(
            worker["full_name"],
            project_name,
            date.toString(qt_date_format()),
            existing,
            self,
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_attendance_record(
                worker["staff_id"], project_id, date.toString("yyyy-MM-dd"), dialog
            )
            self.load_grid()

    # ------------------------------------------------------------------
    # Database save
    # ------------------------------------------------------------------

    # حفظ التغييرات الحالية في قاعدة البيانات.
    def save_attendance_record(self, staff_id, project_id, date, dialog):
        conn = get_connection()

        try:
            if project_id is None:
                existing = conn.execute(
                    """
                    SELECT record_id
                    FROM attendance
                    WHERE staff_id = ?
                      AND project_id IS NULL
                      AND date = ?
                """,
                    (staff_id, date),
                ).fetchone()
            else:
                existing = conn.execute(
                    """
                    SELECT record_id
                    FROM attendance
                    WHERE staff_id = ?
                      AND project_id = ?
                      AND date = ?
                """,
                    (staff_id, project_id, date),
                ).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE attendance
                    SET
                        working_hours = ?,
                        overtime_hours = ?,
                        status = ?,
                        notes = ?
                    WHERE record_id = ?
                """,
                    (
                        dialog.hours.value(),
                        dialog.overtime.value(),
                        dialog.status.currentText(),
                        dialog.notes.text().strip() or None,
                        existing["record_id"],
                    ),
                )
            else:
                record_id = next_child_id(
                    conn, "att", staff_id, project_id or "gen", digits=6
                )

                conn.execute(
                    """
                    INSERT INTO attendance (
                        record_id,
                        staff_id,
                        project_id,
                        date,
                        working_hours,
                        overtime_hours,
                        status,
                        notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        record_id,
                        staff_id,
                        project_id,
                        date,
                        dialog.hours.value(),
                        dialog.overtime.value(),
                        dialog.status.currentText(),
                        dialog.notes.text().strip() or None,
                    ),
                )

            conn.commit()

        except sqlite3.IntegrityError as exc:
            self.error(translate_text(f"Could not save attendance:\n\n{exc}"))

        finally:
            conn.close()

    # حفظ التغييرات الحالية في قاعدة البيانات.
    def save_all(self):
        # Individual cells are saved when their dialog is accepted.
        # This button refreshes the current monthly view.
        self.load_grid()

    # ------------------------------------------------------------------
    # Clear month
    # ------------------------------------------------------------------

    # تنفيذ وظيفة clear_month ضمن هذا الجزء من البرنامج.
    def clear_month(self):
        is_admin = self.view_type.currentText() == "Administration"
        project_id = None if is_admin else self.project.currentData()

        if not is_admin and not project_id:
            self.error("Select a project first.")
            return

        mode_text = "Administration" if is_admin else self.project.currentText()

        answer = QMessageBox.question(
            self,
            translate_text("Confirm"),
            translate_text(
                f"Delete all attendance records for '{mode_text}' in the selected month?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        year = self.year.value()
        month = self.month.currentIndex() + 1
        last_day = self.days_in_selected_month()

        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"

        conn = get_connection()

        try:
            if is_admin:
                conn.execute(
                    """
                    DELETE FROM attendance
                    WHERE project_id IS NULL
                      AND date BETWEEN ? AND ?
                """,
                    (start_date, end_date),
                )
            else:
                conn.execute(
                    """
                    DELETE FROM attendance
                    WHERE project_id = ?
                      AND date BETWEEN ? AND ?
                """,
                    (project_id, start_date, end_date),
                )

            conn.commit()

        finally:
            conn.close()

        self.load_grid()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    # تنفيذ وظيفة update_statistics ضمن هذا الجزء من البرنامج.
    def update_statistics(self):
        project_id = None
        is_admin = self.view_type.currentText() == "Administration"

        if not is_admin:
            project_id = self.project.currentData()
            if not project_id:
                self.reset_statistics()
                return

        year = self.year.value()
        month = self.month.currentIndex() + 1
        last_day = self.days_in_selected_month()

        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"

        conn = get_connection()

        try:
            if is_admin:
                where_sql = """
                    a.project_id IS NULL
                    AND a.date BETWEEN ? AND ?
                """
                params = (start_date, end_date)
            else:
                where_sql = """
                    a.project_id = ?
                    AND a.date BETWEEN ? AND ?
                """
                params = (project_id, start_date, end_date)

            summary = conn.execute(
                f"""
                SELECT
                    COUNT(*) AS total_records,
                    SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END)
                        AS present_count,
                    SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END)
                        AS absent_count,
                    SUM(CASE WHEN a.status = 'Leave' THEN 1 ELSE 0 END)
                        AS leave_count,
                    SUM(CASE WHEN a.status = 'Sick' THEN 1 ELSE 0 END)
                        AS sick_count,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN a.status = 'Present'
                                THEN a.working_hours
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_hours,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN a.status = 'Present'
                                THEN a.overtime_hours
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_overtime
                FROM attendance a
                WHERE {where_sql}
            """,
                params,
            ).fetchone()

            if is_admin:
                worker_count = conn.execute("""
                    SELECT COUNT(*) AS count
                    FROM staff
                    WHERE status = 'Active'
                      AND attendance_type = 'Administration'
                """).fetchone()["count"]
            else:
                worker_count = conn.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM staff s
                    JOIN staff_projects sp ON sp.staff_id = s.staff_id
                    WHERE sp.project_id = ?
                      AND sp.active = 1
                      AND s.status = 'Active'
                      AND s.attendance_type = ?
                """,
                    (project_id, self.view_type.currentText()),
                ).fetchone()["count"]

            self.total_workers.setText(str(worker_count))
            self.present_count.setText(str(summary["present_count"] or 0))
            self.absent_count.setText(str(summary["absent_count"] or 0))
            self.leave_count.setText(str(summary["leave_count"] or 0))
            self.sick_count.setText(str(summary["sick_count"] or 0))
            self.total_hours.setText(f"{summary['total_hours'] or 0:.2f}")
            self.total_overtime.setText(f"{summary['total_overtime'] or 0:.2f}")

            worker_filter = """
                s.status = 'Active'
                AND a.date BETWEEN ? AND ?
            """
            worker_params = [start_date, end_date]

            if is_admin:
                worker_filter += """
                    AND a.project_id IS NULL
                    AND s.attendance_type = 'Administration'
                """
            else:
                worker_filter += """
                    AND a.project_id = ?
                    AND s.attendance_type = ?
                """
                worker_params.insert(0, str(project_id))
                worker_params.append(self.view_type.currentText())

            best = conn.execute(
                f"""
                SELECT
                    s.full_name,
                    SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END)
                        AS present_days
                FROM attendance a
                JOIN staff s ON s.staff_id = a.staff_id
                WHERE {worker_filter}
                GROUP BY a.staff_id, s.full_name
                ORDER BY present_days DESC, s.full_name
                LIMIT 1
            """,
                tuple(worker_params),
            ).fetchone()

            most_absent = conn.execute(
                f"""
                SELECT
                    s.full_name,
                    SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END)
                        AS absent_days
                FROM attendance a
                JOIN staff s ON s.staff_id = a.staff_id
                WHERE {worker_filter}
                GROUP BY a.staff_id, s.full_name
                ORDER BY absent_days DESC, s.full_name
                LIMIT 1
            """,
                tuple(worker_params),
            ).fetchone()

            most_hours = conn.execute(
                f"""
                SELECT
                    s.full_name,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN a.status = 'Present'
                                THEN a.working_hours
                                ELSE 0
                            END
                        ),
                        0
                    ) AS hours                    
                    
                FROM attendance a
                JOIN staff s ON s.staff_id = a.staff_id
                WHERE {worker_filter}
                GROUP BY a.staff_id, s.full_name
                ORDER BY hours DESC, s.full_name
                LIMIT 1
            """,
                tuple(worker_params),
            ).fetchone()

            self.best_attendance.setText(
                f"{best['full_name']} ({best['present_days']})" if best else "-"
            )

            self.most_absent.setText(
                f"{most_absent['full_name']} ({most_absent['absent_days']})"
                if most_absent
                else "-"
            )

            self.most_hours.setText(
                f"{most_hours['full_name']} ({most_hours['hours']:.2f} h)"
                if most_hours
                else "-"
            )

        finally:
            conn.close()

    # تنفيذ وظيفة reset_statistics ضمن هذا الجزء من البرنامج.
    def reset_statistics(self):
        for label in [
            self.total_workers,
            self.present_count,
            self.absent_count,
            self.leave_count,
            self.sick_count,
        ]:
            label.setText("0")

        self.total_hours.setText("0.00")
        self.total_overtime.setText("0.00")
        self.best_attendance.setText("-")
        self.most_absent.setText("-")
        self.most_hours.setText("-")
