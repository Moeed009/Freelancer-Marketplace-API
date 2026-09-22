import io
import uuid

from app.models.enums import JobStatus, RateType
from app.models.file_attachment import FileAttachment, FileAttachmentStatus, FileResourceType
from app.models.job import Job
from app.models.user import User
from app.repositories import file_attachment_repository
from app.routers.files import file_service


def _make_job(db, client: User) -> Job:
    job = Job(
        client_id=client.id,
        title="Build a website",
        description="Need a website built.",
        rate_type=RateType.FIXED,
        budget_min=100,
        budget_max=500,
        status=JobStatus.PUBLISHED,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _upload(client, resource_type, resource_id, filename="test.pdf",
            content=b"%PDF-1.4 test content",
            content_type="application/pdf"):
    return client.post(
        "/Upload_file",
        params={
            "resource_type": resource_type.value,
            "resource_id": str(resource_id),
        },
        files={
            "file": (filename, io.BytesIO(content), content_type),
        },
    )


def test_upload_file_success(
    as_user,
    client_user,
    monkeypatch,
):
    storage_uploads = []

    def fake_upload(file, path, content_type):
        storage_uploads.append(
            {
                "path": path,
                "content_type": content_type,
                "data": file.read(),
            }
        )

    monkeypatch.setattr(file_service.storage, "upload", fake_upload)

    client = as_user(client_user)

    response = _upload(
        client,
        FileResourceType.PROFILE,
        client_user.id,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["owner_id"] == str(client_user.id)
    assert body["resource_type"] == "PROFILE"
    assert body["resource_id"] == str(client_user.id)
    assert body["original_filename"] == "test.pdf"
    assert body["mime_type"] == "application/pdf"
    assert body["size"] > 0
    assert body["status"] == "CONFIRMED"

    assert len(storage_uploads) == 1
    assert storage_uploads[0]["content_type"] == "application/pdf"
    assert storage_uploads[0]["data"] == b"%PDF-1.4 test content"
    assert storage_uploads[0]["path"].startswith(
        f"{client_user.id}/profile/{client_user.id}/"
    )


def test_upload_rejects_invalid_mime_type(
    as_user,
    client_user,
):
    client = as_user(client_user)

    response = _upload(
        client,
        FileResourceType.PROFILE,
        client_user.id,
        filename="test.exe",
        content=b"not allowed",
        content_type="application/x-msdownload",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File type is not allowed"


def test_upload_rejects_empty_file(
    as_user,
    client_user,
):
    client = as_user(client_user)

    response = _upload(
        client,
        FileResourceType.PROFILE,
        client_user.id,
        content=b"",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Empty files are not allowed"


def test_upload_rejects_file_larger_than_10_mb(
    as_user,
    client_user,
):
    client = as_user(client_user)

    large_content = b"x" * (10 * 1024 * 1024 + 1)

    response = _upload(
        client,
        FileResourceType.PROFILE,
        client_user.id,
        content=large_content,
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "File size cannot exceed 10 MB"


def test_upload_profile_for_another_user_is_forbidden(
    as_user,
    client_user,
    other_client_user,
):
    client = as_user(client_user)

    response = _upload(
        client,
        FileResourceType.PROFILE,
        other_client_user.id,
    )

    assert response.status_code == 403


def test_upload_job_for_another_client_is_forbidden(
    as_user,
    client_user,
    other_client_user,
    db,
):
    job = _make_job(db, other_client_user)

    client = as_user(client_user)

    response = _upload(
        client,
        FileResourceType.JOB,
        job.id,
    )

    assert response.status_code == 403


def test_upload_nonexistent_job_returns_404(
    as_user,
    client_user,
):
    client = as_user(client_user)

    response = _upload(
        client,
        FileResourceType.JOB,
        uuid.uuid4(),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_upload_storage_failure_returns_502(
    as_user,
    client_user,
    db,
    monkeypatch,
):
    def fake_upload(file, path, content_type):
        raise RuntimeError("Supabase unavailable")

    monkeypatch.setattr(file_service.storage, "upload", fake_upload)

    client = as_user(client_user)

    response = _upload(
        client,
        FileResourceType.PROFILE,
        client_user.id,
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "File upload failed"

    stored_files = file_attachment_repository.list_by_owner(
        db,
        owner_id=client_user.id,
    )

    assert stored_files == []


def test_list_files_returns_only_authenticated_users_confirmed_files(
    as_user,
    client_user,
    other_client_user,
    db,
    monkeypatch,
):
    monkeypatch.setattr(
        file_service.storage,
        "upload",
        lambda file, path, content_type: None,
    )

    client = as_user(client_user)
    other_client = as_user(other_client_user)

    first = _upload(
        client,
        FileResourceType.PROFILE,
        client_user.id,
        filename="mine-1.pdf",
    )
    second = _upload(
        client,
        FileResourceType.PROFILE,
        client_user.id,
        filename="mine-2.pdf",
    )
    other = _upload(
        other_client,
        FileResourceType.PROFILE,
        other_client_user.id,
        filename="other.pdf",
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert other.status_code == 201

    response = client.get("/List_files")

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 2
    assert {item["original_filename"] for item in body} == {
        "mine-1.pdf",
        "mine-2.pdf",
    }
    assert all(
        item["owner_id"] == str(client_user.id)
        for item in body
    )


def test_list_files_hides_pending_files(
    as_user,
    client_user,
    db,
):
    file_attachment_repository.create(
        db,
        owner_id=client_user.id,
        resource_type=FileResourceType.PROFILE,
        resource_id=client_user.id,
        original_filename="pending.pdf",
        storage_path=f"{client_user.id}/profile/{client_user.id}/pending.pdf",
        mime_type="application/pdf",
        size=100,
    )

    response = as_user(client_user).get("/List_files")

    assert response.status_code == 200
    assert response.json() == []


def test_list_files_requires_authentication(anon_client):
    response = anon_client.get("/List_files")

    assert response.status_code == 401


def test_download_file_returns_signed_url(
    as_user,
    client_user,
    db,
    monkeypatch,
):
    monkeypatch.setattr(
        file_service.storage,
        "upload",
        lambda file, path, content_type: None,
    )

    upload_response = _upload(
        as_user(client_user),
        FileResourceType.PROFILE,
        client_user.id,
    )

    assert upload_response.status_code == 201

    file_id = upload_response.json()["id"]

    monkeypatch.setattr(
        file_service.storage,
        "create_signed_url",
        lambda path, expires_in=600: "https://signed.example/test.pdf",
    )

    response = as_user(client_user).get(
        "/Download_file",
        params={"file_id": file_id},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["file_id"] == file_id
    assert body["filename"] == "test.pdf"
    assert body["mime_type"] == "application/pdf"
    assert body["expires_in"] == 600
    assert body["download_url"] == "https://signed.example/test.pdf"


def test_download_unknown_file_returns_404(
    as_user,
    client_user,
):
    response = as_user(client_user).get(
        "/Download_file",
        params={"file_id": str(uuid.uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_download_file_from_unauthorized_resource_is_forbidden(
    as_user,
    client_user,
    other_client_user,
    db,
    monkeypatch,
):
    monkeypatch.setattr(
        file_service.storage,
        "upload",
        lambda file, path, content_type: None,
    )

    upload_response = _upload(
        as_user(other_client_user),
        FileResourceType.PROFILE,
        other_client_user.id,
    )

    assert upload_response.status_code == 201

    file_id = upload_response.json()["id"]

    response = as_user(client_user).get(
        "/Download_file",
        params={"file_id": file_id},
    )

    assert response.status_code == 403


def test_download_signed_url_failure_returns_502(
    as_user,
    client_user,
    monkeypatch,
):
    monkeypatch.setattr(
        file_service.storage,
        "upload",
        lambda file, path, content_type: None,
    )

    upload_response = _upload(
        as_user(client_user),
        FileResourceType.PROFILE,
        client_user.id,
    )

    assert upload_response.status_code == 201

    monkeypatch.setattr(
        file_service.storage,
        "create_signed_url",
        lambda path, expires_in=600: (_ for _ in ()).throw(
            RuntimeError("Supabase unavailable")
        ),
    )

    response = as_user(client_user).get(
        "/Download_file",
        params={"file_id": upload_response.json()["id"]},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to generate download URL"


def test_delete_file_removes_storage_and_database_record(
    as_user,
    client_user,
    db,
    monkeypatch,
):
    monkeypatch.setattr(
        file_service.storage,
        "upload",
        lambda file, path, content_type: None,
    )

    upload_response = _upload(
        as_user(client_user),
        FileResourceType.PROFILE,
        client_user.id,
    )

    assert upload_response.status_code == 201

    file_id = upload_response.json()["id"]
    deleted_paths = []

    monkeypatch.setattr(
        file_service.storage,
        "delete",
        lambda path: deleted_paths.append(path),
    )

    response = as_user(client_user).delete(
        "/Delete_file",
        params={"file_id": file_id},
    )

    assert response.status_code == 204
    assert response.content == b""

    assert len(deleted_paths) == 1

    assert db.get(
        FileAttachment,
        uuid.UUID(file_id),
    ) is None


def test_delete_unknown_file_returns_404(
    as_user,
    client_user,
):
    response = as_user(client_user).delete(
        "/Delete_file",
        params={"file_id": str(uuid.uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_delete_file_from_unauthorized_resource_is_forbidden(
    as_user,
    client_user,
    other_client_user,
    monkeypatch,
):
    monkeypatch.setattr(
        file_service.storage,
        "upload",
        lambda file, path, content_type: None,
    )

    upload_response = _upload(
        as_user(other_client_user),
        FileResourceType.PROFILE,
        other_client_user.id,
    )

    assert upload_response.status_code == 201

    response = as_user(client_user).delete(
        "/Delete_file",
        params={"file_id": upload_response.json()["id"]},
    )

    assert response.status_code == 403


def test_delete_storage_failure_returns_502(
    as_user,
    client_user,
    db,
    monkeypatch,
):
    monkeypatch.setattr(
        file_service.storage,
        "upload",
        lambda file, path, content_type: None,
    )

    upload_response = _upload(
        as_user(client_user),
        FileResourceType.PROFILE,
        client_user.id,
    )

    assert upload_response.status_code == 201

    file_id = upload_response.json()["id"]

    def fake_delete(path):
        raise RuntimeError("Supabase unavailable")

    monkeypatch.setattr(
        file_service.storage,
        "delete",
        fake_delete,
    )

    response = as_user(client_user).delete(
        "/Delete_file",
        params={"file_id": file_id},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to delete file from storage"

    stored = db.get(
        FileAttachment,
        uuid.UUID(file_id),
    )

    assert stored is not None
    assert stored.status == FileAttachmentStatus.CONFIRMED
