"""Lazy page exports.

Keeping page imports lazy prevents lightweight services such as ``pages.id_service``
from importing the entire Qt UI stack. The public ``from pages import X`` API remains unchanged.
"""
from __future__ import annotations

from importlib import import_module

_PAGE_EXPORTS = {
    "AccountingPage": ("pages.accounting_page", "AccountingPage"),
    "AdministrationPage": ("pages.administration_page", "AdministrationPage"),
    "AIAssistantDialog": ("pages.ai_assistant_dialog", "AIAssistantDialog"),
    "AttendancePage": ("pages.attendance_page", "AttendancePage"),
    "BackupPage": ("pages.backup_page", "BackupPage"),
    "CompanyPage": ("pages.company_page", "CompanyPage"),
    "ConstructionControlPage": ("pages.construction_control_page", "ConstructionControlPage"),
    "ContactsPage": ("pages.contacts_page", "ContactsPage"),
    "DashboardPage": ("pages.dashboard_page", "DashboardPage"),
    "DebtsPage": ("pages.debts_page", "DebtsPage"),
    "DocumentGenerationPage": ("pages.document_generation_page", "DocumentGenerationPage"),
    "DocumentsPage": ("pages.documents_page", "DocumentsPage"),
    "ExpensesPage": ("pages.expenses_page", "ExpensesPage"),
    "IncomePage": ("pages.income_page", "IncomePage"),
    "ManagementPage": ("pages.management_page", "ManagementPage"),
    "MediaPage": ("pages.media_page", "MediaPage"),
    "MetrePage": ("pages.metre_page", "MetrePage"),
    "PayrollPage": ("pages.payroll_page", "PayrollPage"),
    "ProcurementPage": ("pages.procurement_page", "ProcurementPage"),
    "ProgressPage": ("pages.progress_page", "ProgressPage"),
    "ProjectCloseoutPage": ("pages.project_closeout_page", "ProjectCloseoutPage"),
    "ProjectControlPage": ("pages.project_control_page", "ProjectControlPage"),
    "ProjectGovernancePage": ("pages.project_governance_page", "ProjectGovernancePage"),
    "ProjectProfitabilityPage": ("pages.project_profitability_page", "ProjectProfitabilityPage"),
    "ProjectsPage": ("pages.projects_page", "ProjectsPage"),
    "ReportsPage": ("pages.reports_page", "ReportsPage"),
    "SettingsPage": ("pages.settings_page", "SettingsPage"),
    "SiteOperationsPage": ("pages.site_operations_page", "SiteOperationsPage"),
    "StaffPage": ("pages.staff_page", "StaffPage"),
    "StatisticsPage": ("pages.statistics_page", "StatisticsPage"),
    "SupplementaryPage": ("pages.supplementary_page", "SupplementaryPage"),
    "VehiclesPage": ("pages.vehicles_page", "VehiclesPage"),
}

__all__ = list(_PAGE_EXPORTS)

def __getattr__(name: str):
    spec = _PAGE_EXPORTS.get(name)
    if spec is None:
        raise AttributeError(name)
    module_name, attr_name = spec
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
