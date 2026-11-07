import hashlib
import json
import os
from datetime import datetime, timezone

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings


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
        content = container.get_blob_client(
            item.name
        ).download_blob().readall()
        records.append(json.loads(content))

    return sorted(
        records,
        key=lambda record: record["shared_at"],
        reverse=True,
    )
