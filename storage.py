import hashlib
import json
import os
from datetime import datetime, timezone


from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core import MatchConditions
from azure.core.exceptions import ResourceModifiedError


def get_container():
    service = BlobServiceClient.from_connection_string(
        os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    )
    return service.get_container_client("ffm-data")


def share_grant(grant, workspace_id="demo-agency"):
    # A stable filename prevents duplicate shares of the same grant.
    grant_key = hashlib.sha256(
        str(grant["id"]).encode("utf-8")
    ).hexdigest()

    blob_name = f"workspaces/{workspace_id}/grants/{grant_key}.json"

    record = {
        "grant": grant,
        "status": "Not Reviewed",
        "shared_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        get_container().get_blob_client(blob_name).upload_blob(
            json.dumps(record, ensure_ascii=False).encode("utf-8"),
            overwrite=False,
            content_settings=ContentSettings(
                content_type="application/json"
            ),
        )
        return True
    except ResourceExistsError:
        return False


def list_shared_grants(workspace_id="demo-agency"):
    container = get_container()
    prefix = f"workspaces/{workspace_id}/grants/"
    records = []

    for item in container.list_blobs(name_starts_with=prefix):
        download = container.get_blob_client(
            item.name
        ).download_blob()

        record = json.loads(download.readall())
        record["_blob_name"] = item.name
        record["_etag"] = download.properties.etag
        records.append(record)

    return sorted(
        records,
        key=lambda record: record["shared_at"],
        reverse=True,
    )

def update_review_status(record, status):
    allowed = {"Not Reviewed", "Under Review", "Pursue", "Pass"}

    if status not in allowed:
        raise ValueError("Invalid review status")

    updated = {
        key: value
        for key, value in record.items()
        if not key.startswith("_")
    }
    updated["status"] = status
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()

    blob = get_container().get_blob_client(record["_blob_name"])

    try:
        blob.upload_blob(
            json.dumps(updated, ensure_ascii=False).encode("utf-8"),
            overwrite=True,
            etag=record["_etag"],
            match_condition=MatchConditions.IfNotModified,
            content_settings=ContentSettings(
                content_type="application/json"
            ),
        )
        return True
    except ResourceModifiedError:
        return False
