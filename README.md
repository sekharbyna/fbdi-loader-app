# Fusion FBDI Load Console

Web application that automates the Oracle Cloud ERP File-Based Data Import path:

1. You prepare data in the official FBDI XLSM and click **Generate CSV File**.
2. The app uploads that ZIP to UCM (`uploadFileToUCM`).
3. It submits **Load Interface File for Import** (`InterfaceLoaderController`) so CSV rows land in the interface tables (`GL_INTERFACE`, `AP_INVOICES_INTERFACE`, `FA_MASS_ADDITIONS`, …).
4. Optionally it submits the module import ESS job so rows move into application tables (journals, invoices, assets, suppliers).

```
XLSM template
    → ZIP of CSVs
        → UCM account (fin/generalLedger/import, …)
            → interface tables
                → application tables
```

## What this is (and is not)

- This is an **operator console + REST orchestrator**. It does not replace the FBDI template macros.
- It does **not** parse or rewrite CSV columns. The ZIP must already match Oracle’s file names.
- Interface IDs and ESS parameter order can differ by pod/release. Confirm them with **Lookup Interface ID** before a cutover.

## Supported objects (catalog-driven)

| Object | UCM account | Interface tables | Load job | Import job |
| --- | --- | --- | --- | --- |
| GL Journals | `fin/generalLedger/import` | `GL_INTERFACE` | Load Interface File for Import | Import Journals |
| Payables Invoices | `fin/payables/import` | `AP_INVOICES_INTERFACE`, `AP_INVOICE_LINES_INTERFACE` | Load Interface File for Import | Import Payables Invoices |
| FA Mass Additions | `fin/assets/import` | `FA_MASS_ADDITIONS` | Load Interface File for Import | Post Mass Additions |
| Suppliers | `prc/supplier/import` | `POZ_SUPPLIERS_INT` (+ sites/addresses) | Load Interface File for Import | Import Suppliers |

Add more objects in `app/catalog.py`.

## Run locally

### Windows PowerShell

Install Python 3.11+ from https://www.python.org/downloads/ and tick **Add python.exe to PATH**. Unzip the console, then:

```powershell
cd $HOME\Downloads\fbdi-loader-app
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run.ps1
```

Or run the commands yourself:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000

### Linux / macOS

```bash
cd fbdi-loader-app
chmod +x run.sh
./run.sh
```

## Integration user

The Fusion user must be able to:

- Call `/fscmRestApi/resources/11.13.18.05/erpintegrations`
- Upload to the target UCM account
- Submit ESS jobs (`Load Interface File for Import` and the module import)

Typical seed roles: integration specialist + the financials duty that owns the import process. Basic auth is used against the REST resource (same pattern as Oracle’s published `erpintegrations` examples). Prefer a dedicated integration user, not a named end-user.

## Two load modes

**Two-step (recommended)**

1. `POST erpintegrations` `OperationName=uploadFileToUCM` → `DocumentId`
2. `POST erpintegrations` `OperationName=submitESSJobRequest`
   - Job: `oracle/apps/ess/financials/commonModules/shared/common/interfaceLoader` / `InterfaceLoaderController`
   - Parameters: `<InterfaceId>,<DocumentId>,N,N`
3. After the load job is `SUCCEEDED`, submit the module import job with its own parameter list.

**One-shot**

`OperationName=importBulkData` uploads the ZIP and chains load + import. Use `JobOptions` such as:

`ExtractFileType=ALL,InterfaceDetails=<InterfaceId>,ImportOption=Y,PurgeOption=N`

One-shot is faster but harder to debug when the interface load succeeds and the import fails.

Leave **Wait for each ESS job** checked so the app polls `ESSJobStatusRF` after Load Interface File for Import. Import is submitted only when that job ends in `SUCCEEDED` or `WARNING`. ESS logs can be pulled with **Download ESS log**.

## Confirm Interface ID on your pod

```json
POST /fscmRestApi/resources/11.13.18.05/erpprocesses
{
  "OperationName": "inboundProcessDetails",
  "ProcessName": "oracle/apps/ess/financials/payables/invoices/transactions,APXIIMPT"
}
```

The response includes `InterfaceId` and `UcmAccount`. The console **Lookup Interface ID** button calls this for the selected object.

Catalog starting points (always verify):

- Payables Standard Invoice Import: `1`
- Journal Import: `15`
- Supplier Import: `24`

## Check that interface rows actually landed

Use OTBI / SQL Developer / BI Publisher against the interface table and the ESS `LOAD_REQUEST_ID` returned by the console. Example for journals:

```sql
SELECT status, user_je_source_name, accounting_date, currency_code,
       entered_dr, entered_cr, load_request_id, COUNT(*) recs
FROM   gl_interface
WHERE  load_request_id = :load_request_id
GROUP  BY status, user_je_source_name, accounting_date, currency_code,
          entered_dr, entered_cr, load_request_id;
```

Then watch **Scheduled Processes** for `SUCCEEDED` / `WARNING` / `ERROR` and download the ESS log if rows reject.

## Common failures

| Symptom | Likely cause |
| --- | --- |
| File uploaded, 0 rows in interface | Wrong UCM account, or ZIP CSV names do not match the template |
| Load job ERROR | Bad Interface ID, corrupt ZIP, or CSV encoding/header mismatch |
| Import WARNING | Invalid combinations, closed period, source/category not defined, supplier site missing |
| `ReqstId` missing | Integration user cannot submit that ESS job |
| DocumentId missing | UCM account string format — REST wants `fin$/generalLedger$/import$` |

## Next extensions

- Poll until `SUCCEEDED` then auto-submit the import job
- Download ESS log/out files (`ESSJobExecutionDetailsRF`)
- n8n webhook wrapper for overnight batches
- Callback URL on `importBulkData` (`ErpImportBulkDataEvent`)
- Pre-validate CSV required columns before upload
