"""Thin client for Oracle Fusion ERP Integrations REST APIs (stdlib only)."""

from __future__ import annotations

import base64
import json
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

TERMINAL_STATUSES = {
    "SUCCEEDED",
    "ERROR",
    "WARNING",
    "CANCELLED",
    "CANCELED",
    "EXPIRED",
    "VALIDATION_FAILED",
}

REST_VERSION = "11.13.18.05"


class OracleError(Exception):
    pass


class OracleERPClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: float = 180.0):
        self.base_url = base_url.rstrip("/")
        token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
        self.timeout = timeout
        self.auth_header = f"Basic {token}"
        self.ssl_context = ssl.create_default_context()

    @property
    def integrations_url(self) -> str:
        return f"{self.base_url}/fscmRestApi/resources/{REST_VERSION}/erpintegrations"

    @property
    def processes_url(self) -> str:
        return f"{self.base_url}/fscmRestApi/resources/{REST_VERSION}/erpprocesses"

    def _request(self, method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None
        headers = {
            "Accept": "application/json",
            "Authorization": self.auth_header,
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/vnd.oracle.adf.resourceitem+json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_context) as resp:
                raw = resp.read()
                status = resp.status
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:4000]
            raise OracleError(f"Oracle Cloud returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise OracleError(f"Could not reach Oracle Cloud: {exc.reason}") from exc
        if not raw:
            return {"http_status": status}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {"http_status": status, "raw": raw.decode("utf-8", errors="replace")[:2000]}

    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", url, payload)

    def _get(self, url: str) -> dict[str, Any]:
        return self._request("GET", url)

    def ping(self) -> dict[str, Any]:
        url = f"{self.integrations_url}?limit=1"
        self._get(url)
        return {"ok": True}

    def upload_file_to_ucm(
        self,
        file_bytes: bytes,
        file_name: str,
        document_account: str,
        content_type: str = "zip",
    ) -> dict[str, Any]:
        payload = {
            "OperationName": "uploadFileToUCM",
            "DocumentContent": base64.b64encode(file_bytes).decode("ascii"),
            "ContentType": content_type,
            "FileName": file_name,
            "DocumentAccount": document_account,
        }
        return self._post(self.integrations_url, payload)

    def submit_ess_job(
        self,
        job_package_name: str,
        job_def_name: str,
        ess_parameters: str,
    ) -> dict[str, Any]:
        payload = {
            "OperationName": "submitESSJobRequest",
            "JobPackageName": job_package_name,
            "JobDefName": job_def_name,
            "ESSParameters": ess_parameters,
        }
        return self._post(self.integrations_url, payload)

    def import_bulk_data(
        self,
        file_bytes: bytes,
        file_name: str,
        document_account: str,
        job_name: str,
        parameter_list: str,
        job_options: str,
        notification_code: str = "10",
        callback_url: str = "#NULL",
        content_type: str = "zip",
    ) -> dict[str, Any]:
        payload = {
            "OperationName": "importBulkData",
            "DocumentContent": base64.b64encode(file_bytes).decode("ascii"),
            "ContentType": content_type,
            "FileName": file_name,
            "DocumentAccount": document_account,
            "JobName": job_name,
            "ParameterList": parameter_list,
            "NotificationCode": notification_code,
            "CallbackURL": callback_url,
            "JobOptions": job_options,
        }
        return self._post(self.integrations_url, payload)

    def get_ess_job_status(self, request_id: str) -> dict[str, Any]:
        url = f"{self.integrations_url}?finder=ESSJobStatusRF;requestId={request_id}"
        return self._get(url)

    def get_ess_job_details(self, request_id: str, file_type: str = "log") -> dict[str, Any]:
        url = (
            f"{self.integrations_url}"
            f"?finder=ESSJobExecutionDetailsRF;requestId={request_id},fileType={file_type}"
        )
        return self._get(url)

    def inbound_process_details(self, job_name: str) -> dict[str, Any]:
        payload = {
            "OperationName": "inboundProcessDetails",
            "ProcessName": job_name,
        }
        return self._post(self.processes_url, payload)

    @staticmethod
    def extract_request_status(payload: dict[str, Any]) -> str:
        if payload.get("RequestStatus"):
            return str(payload["RequestStatus"]).upper()
        items = payload.get("items") or []
        if items and items[0].get("RequestStatus"):
            return str(items[0]["RequestStatus"]).upper()
        return ""

    def wait_for_job(
        self,
        request_id: str,
        timeout_seconds: int = 300,
        interval_seconds: int = 8,
    ) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        last: dict[str, Any] = {}
        while time.time() < deadline:
            last = self.get_ess_job_status(request_id)
            status = self.extract_request_status(last)
            last["_normalizedStatus"] = status
            if status in TERMINAL_STATUSES:
                return last
            time.sleep(interval_seconds)
        last["_normalizedStatus"] = self.extract_request_status(last) or "TIMEOUT"
        last["_timedOut"] = True
        return last
