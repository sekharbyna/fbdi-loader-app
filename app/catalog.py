"""Catalog of supported FBDI objects.

Interface IDs and job paths can differ slightly by release. Confirm in your
pod with POST /fscmRestApi/resources/11.13.18.05/erpprocesses
  OperationName = inboundProcessDetails
  JobName       = <package>,<def>

UCM account format for REST is slash-delimited with $ separators:
  fin/generalLedger/import  ->  fin$/generalLedger$/import$
"""

from __future__ import annotations

LOADER_PACKAGE = "oracle/apps/ess/financials/commonModules/shared/common/interfaceLoader"
LOADER_DEF = "InterfaceLoaderController"

CATALOG: dict[str, dict] = {
    "gl_journals": {
        "key": "gl_journals",
        "label": "GL Journals",
        "module": "General Ledger",
        "template": "JournalImportTemplate.xlsm",
        "csv_names": ["GlInterface.csv"],
        "ucm_account": "fin$/generalLedger$/import$",
        "ucm_account_ui": "fin/generalLedger/import",
        "interface_tables": ["GL_INTERFACE"],
        "interface_id": "15",
        "load_job": {
            "package": LOADER_PACKAGE,
            "definition": LOADER_DEF,
            "display": "Load Interface File for Import",
        },
        "import_job": {
            "package": "oracle/apps/ess/financials/generalLedger/programs/common",
            "definition": "JournalImportLauncher",
            "display": "Import Journals",
            "job_name": "oracle/apps/ess/financials/generalLedger/programs/common,JournalImportLauncher",
        },
        "import_parameters": [
            {
                "name": "data_access_set",
                "label": "Data Access Set",
                "hint": "Name or ID of the data access set that owns the ledger",
                "required": True,
            },
            {
                "name": "source",
                "label": "Journal Source",
                "hint": "Must match USER_JE_SOURCE_NAME in the CSV (e.g. Spreadsheet)",
                "required": True,
                "default": "Spreadsheet",
            },
            {
                "name": "ledger",
                "label": "Ledger",
                "hint": "Ledger name or ledger_id. Use #NULL to import all ledgers in the file",
                "required": False,
                "default": "#NULL",
            },
            {
                "name": "group_id",
                "label": "Group ID",
                "hint": "GL_INTERFACE.GROUP_ID / Interface Group Identifier. #NULL = all",
                "required": False,
                "default": "#NULL",
            },
            {
                "name": "post_errors_to_suspense",
                "label": "Post Errors to Suspense",
                "hint": "N or Y",
                "required": True,
                "default": "N",
            },
            {
                "name": "create_summary_journals",
                "label": "Create Summary Journals",
                "hint": "N or Y",
                "required": True,
                "default": "N",
            },
            {
                "name": "import_dff",
                "label": "Import Descriptive Flexfields",
                "hint": "N or Y",
                "required": True,
                "default": "N",
            },
        ],
        "verify_sql": (
            "SELECT status, ledger_id, user_je_source_name, user_je_category_name,\n"
            "       accounting_date, currency_code, entered_dr, entered_cr,\n"
            "       reference1, group_id, load_request_id, COUNT(*) recs\n"
            "FROM   gl_interface\n"
            "WHERE  load_request_id = :load_request_id\n"
            "GROUP  BY status, ledger_id, user_je_source_name, user_je_category_name,\n"
            "          accounting_date, currency_code, entered_dr, entered_cr,\n"
            "          reference1, group_id, load_request_id"
        ),
        "notes": [
            "Generate the ZIP from the FBDI XLSM using Generate CSV File — do not hand-rename CSV tabs.",
            "STATUS in GlInterface.csv must be NEW.",
            "After Load Interface File succeeds, rows sit in GL_INTERFACE until Import Journals runs.",
            "Confirm Interface ID 15 against erpprocesses inboundProcessDetails on your pod.",
        ],
    },
    "ap_invoices": {
        "key": "ap_invoices",
        "label": "Payables Invoices",
        "module": "Payables",
        "template": "PayablesStandardInvoiceImportTemplate.xlsm",
        "csv_names": ["ApInvoicesInterface.csv", "ApInvoiceLinesInterface.csv"],
        "ucm_account": "fin$/payables$/import$",
        "ucm_account_ui": "fin/payables/import",
        "interface_tables": ["AP_INVOICES_INTERFACE", "AP_INVOICE_LINES_INTERFACE"],
        "interface_id": "1",
        "load_job": {
            "package": LOADER_PACKAGE,
            "definition": LOADER_DEF,
            "display": "Load Interface File for Import",
        },
        "import_job": {
            "package": "oracle/apps/ess/financials/payables/invoices/transactions",
            "definition": "APXIIMPT",
            "display": "Import Payables Invoices",
            "job_name": "oracle/apps/ess/financials/payables/invoices/transactions,APXIIMPT",
        },
        "import_parameters": [
            {
                "name": "business_unit",
                "label": "Business Unit",
                "hint": "Payables BU name. #NULL = all BUs in the file",
                "required": False,
                "default": "#NULL",
            },
            {
                "name": "source",
                "label": "Source",
                "hint": "Must match invoice SOURCE in the CSV",
                "required": True,
                "default": "Spreadsheet",
            },
            {
                "name": "ledger",
                "label": "Ledger",
                "hint": "Optional ledger filter",
                "required": False,
                "default": "#NULL",
            },
            {
                "name": "group",
                "label": "Invoice Group",
                "hint": "Optional group name",
                "required": False,
                "default": "#NULL",
            },
            {
                "name": "invoice_status",
                "label": "Invoice Status",
                "hint": "Leave #NULL unless you need a forced status",
                "required": False,
                "default": "#NULL",
            },
            {
                "name": "hold_reason",
                "label": "Hold Reason",
                "required": False,
                "default": "#NULL",
            },
            {
                "name": "p7",
                "label": "Reserved / extra param 7",
                "required": False,
                "default": "#NULL",
            },
            {
                "name": "import_set",
                "label": "Import Set / Invoice Gateway",
                "hint": "Often INVOICE or INVOICE GATEWAY depending on source",
                "required": False,
                "default": "INVOICE",
            },
        ],
        "verify_sql": (
            "SELECT invoice_num, source, org_id, vendor_name, invoice_amount,\n"
            "       status, load_request_id\n"
            "FROM   ap_invoices_interface\n"
            "WHERE  load_request_id = :load_request_id"
        ),
        "notes": [
            "ZIP must contain both header and line CSVs with the exact FBDI file names.",
            "Interface ID 1 is the documented value for Import Payables Invoices.",
            "Import Payables Invoices parameter order is pod-sensitive — confirm with erpprocesses.",
        ],
    },
    "fa_mass_additions": {
        "key": "fa_mass_additions",
        "label": "FA Mass Additions",
        "module": "Fixed Assets",
        "template": "MassAdditionsImportTemplate.xlsm",
        "csv_names": ["FaMassAdditions.csv"],
        "ucm_account": "fin$/assets$/import$",
        "ucm_account_ui": "fin/assets/import",
        "interface_tables": ["FA_MASS_ADDITIONS"],
        "interface_id": "",
        "load_job": {
            "package": LOADER_PACKAGE,
            "definition": LOADER_DEF,
            "display": "Load Interface File for Import",
        },
        "import_job": {
            "package": "oracle/apps/ess/financials/assets/additions",
            "definition": "MassAdditionsPost",
            "display": "Post Mass Additions",
            "job_name": "oracle/apps/ess/financials/assets/additions,MassAdditionsPost",
        },
        "import_parameters": [
            {
                "name": "book",
                "label": "Asset Book",
                "hint": "Corporate / tax book name. Required for Post Mass Additions",
                "required": True,
            },
        ],
        "verify_sql": (
            "SELECT mass_addition_id, asset_number, book_type_code, posting_status,\n"
            "       queue_name, fixed_assets_cost, load_request_id\n"
            "FROM   fa_mass_additions\n"
            "WHERE  load_request_id = :load_request_id\n"
            "   OR  posting_status IN ('NEW','ON HOLD','POST')"
        ),
        "notes": [
            "Stage 1 only loads FA_MASS_ADDITIONS. Stage 2 is Post Mass Additions, which creates FA_ADDITIONS rows.",
            "Set POSTING_STATUS = POST (and clear holds) before posting.",
            "Look up Interface ID on your pod — Assets IDs vary by release. Use Lookup Interface ID in this app.",
        ],
    },
    "suppliers": {
        "key": "suppliers",
        "label": "Suppliers",
        "module": "Procurement",
        "template": "SupplierImportTemplate.xlsm",
        "csv_names": [
            "PozSuppliersInt.csv",
            "PozSupplierAddressesInt.csv",
            "PozSupplierSitesInt.csv",
        ],
        "ucm_account": "prc$/supplier$/import$",
        "ucm_account_ui": "prc/supplier/import",
        "interface_tables": [
            "POZ_SUPPLIERS_INT",
            "POZ_SUPPLIER_ADDRESSES_INT",
            "POZ_SUPPLIER_SITES_INT",
        ],
        "interface_id": "24",
        "load_job": {
            "package": LOADER_PACKAGE,
            "definition": LOADER_DEF,
            "display": "Load Interface File for Import",
        },
        "import_job": {
            "package": "oracle/apps/ess/prc/poz/supplierImport",
            "definition": "ImportSuppliers",
            "display": "Import Suppliers",
            "job_name": "oracle/apps/ess/prc/poz/supplierImport,ImportSuppliers",
        },
        "import_parameters": [
            {
                "name": "import_options",
                "label": "Import Options",
                "hint": "ALL, NEW, or REJECTED",
                "required": True,
                "default": "ALL",
            },
            {
                "name": "report_exceptions_only",
                "label": "Report Exceptions Only",
                "hint": "N or Y",
                "required": True,
                "default": "N",
            },
            {
                "name": "batch_id",
                "label": "Batch ID",
                "hint": "Must match BATCH_ID in PozSuppliersInt.csv",
                "required": False,
                "default": "Batch_A123452",
            },
        ],
        "verify_sql": (
            "SELECT batch_id, supplier_name, status, load_request_id\n"
            "FROM   poz_suppliers_int\n"
            "WHERE  load_request_id = :load_request_id"
        ),
        "notes": [
            "Supplier FBDI can be header-only (PozSuppliersInt.csv) or multi-file (addresses, sites, contacts).",
            "Interface ID 24 is confirmed on many pods for Load Interface File for Import.",
            "Stage 2 job is Import Suppliers (supplierImport/ImportSuppliers), not SupplierImportEss.",
            "ParameterList order: Import Options, Report Exceptions Only, Batch ID — e.g. ALL,N,Batch_A123452.",
            "ReqstId -1 means Fusion rejected the job name or parameter list. Do not poll that id.",
        ],
    },
}


def list_objects() -> list[dict]:
    return [
        {
            "key": item["key"],
            "label": item["label"],
            "module": item["module"],
            "template": item["template"],
            "ucm_account_ui": item["ucm_account_ui"],
            "interface_tables": item["interface_tables"],
            "interface_id": item["interface_id"],
            "import_job_display": item["import_job"]["display"],
            "import_parameters": item["import_parameters"],
            "notes": item["notes"],
            "verify_sql": item["verify_sql"],
        }
        for item in CATALOG.values()
    ]


def get_object(key: str) -> dict:
    if key not in CATALOG:
        raise KeyError(f"Unknown FBDI object: {key}")
    return CATALOG[key]
