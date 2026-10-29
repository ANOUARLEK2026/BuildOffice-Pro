# ============================================================
# شرح الملف: pages/__init__.py
# هذا الملف جزء من واجهات الصفحات والنوافذ الخاصة بالتطبيق.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================

from pages.accounting_page import AccountingPage

from .administration_page import AdministrationPage
from .ai_assistant_dialog import AIAssistantDialog
from .attendance_page import AttendancePage
from .accounting_page import AccountingPage
from .backup_page import BackupPage
from .company_page import CompanyPage
from .construction_control_page import ConstructionControlPage
from .contacts_page import ContactsPage
from .dashboard_page import DashboardPage
from .debts_page import DebtsPage
from .document_generation_page import DocumentGenerationPage
from .documents_page import DocumentsPage
from .expenses_page import ExpensesPage
from .income_page import IncomePage
from .management_page import ManagementPage
from .media_page import MediaPage
from .metre_page import MetrePage
from .payroll_page import PayrollPage
from .procurement_page import ProcurementPage
from .progress_page import ProgressPage
from .project_closeout_page import ProjectCloseoutPage
from .project_control_page import ProjectControlPage
from .project_governance_page import ProjectGovernancePage
from .project_profitability_page import ProjectProfitabilityPage
from .projects_page import ProjectsPage
from .reports_page import ReportsPage
from .settings_page import SettingsPage
from .site_operations_page import SiteOperationsPage
from .staff_page import StaffPage
from .statistics_page import StatisticsPage
from .supplementary_page import SupplementaryPage
from .vehicles_page import VehiclesPage

__all__ = [
    "AIAssistantDialog",
    "AccountingPage",
    "AdministrationPage",
    "AttendancePage",
    "BackupPage",
    "CompanyPage",
    "ConstructionControlPage",
    "ContactsPage",
    "DashboardPage",
    "DebtsPage",
    "DocumentGenerationPage",
    "DocumentsPage",
    "ExpensesPage",
    "IncomePage",
    "ManagementPage",
    "MediaPage",
    "MetrePage",
    "PayrollPage",
    "ProcurementPage",
    "ProgressPage",
    "ProjectCloseoutPage",
    "ProjectControlPage",
    "ProjectGovernancePage",
    "ProjectProfitabilityPage",
    "ProjectsPage",
    "ReportsPage",
    "SettingsPage",
    "SiteOperationsPage",
    "StaffPage",
    "StatisticsPage",
    "SupplementaryPage",
    "VehiclesPage",
]
