from app.models.enums import JobStatus, RateType
from app.models.job import Job
from app.models.user import User


def _make_job(
    db,
    client: User,
    *,
    title="Build a website",
    status=JobStatus.PUBLISHED,
) -> Job:
    job = Job(
        client_id=client.id,
        title=title,
        description="Need a website built.",
        rate_type=RateType.FIXED,
        budget_min=100,
        budget_max=500,
        status=status,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def test_client_can_create_a_job(as_user, client_user):
    c = as_user(client_user)

    payload = {
        "title": "Build a landing page",
        "description": "Simple one-pager.",
        "rate_type": "FIXED",
        "budget_min": 50,
        "budget_max": 200,
        "skill_ids": [],
    }

    response = c.post("/Create_job", json=payload)

    assert response.status_code == 201

    body = response.json()

    assert body["title"] == "Build a landing page"
    assert body["status"] == "DRAFT"


def test_freelancer_cannot_create_a_job(as_user, freelancer_user):
    c = as_user(freelancer_user)

    payload = {
        "title": "Build a landing page",
        "description": "Simple one-pager.",
        "rate_type": "FIXED",
        "budget_min": 50,
        "budget_max": 200,
        "skill_ids": [],
    }

    response = c.post("/Create_job", json=payload)

    assert response.status_code == 403


def test_search_jobs_only_returns_published_by_default(
    as_user,
    freelancer_user,
    client_user,
    db,
):
    _make_job(
        db,
        client_user,
        title="Published job",
        status=JobStatus.PUBLISHED,
    )

    _make_job(
        db,
        client_user,
        title="Draft job",
        status=JobStatus.DRAFT,
    )

    c = as_user(freelancer_user)

    response = c.get("/Search_job")

    assert response.status_code == 200

    titles = [
        item["title"]
        for item in response.json()["items"]
    ]

    assert "Published job" in titles
    assert "Draft job" not in titles


def test_list_my_jobs_returns_jobs_of_any_status(
    as_user,
    client_user,
    other_client_user,
    db,
):
    _make_job(
        db,
        client_user,
        title="My draft job",
        status=JobStatus.DRAFT,
    )

    _make_job(
        db,
        client_user,
        title="My published job",
        status=JobStatus.PUBLISHED,
    )

    _make_job(
        db,
        other_client_user,
        title="Someone else's job",
        status=JobStatus.PUBLISHED,
    )

    c = as_user(client_user)

    response = c.get(
        "/Search_job",
        params={"mine": "true"},
    )

    assert response.status_code == 200

    titles = {
        item["title"]
        for item in response.json()["items"]
    }

    assert titles == {
        "My draft job",
        "My published job",
    }


def test_list_my_jobs_requires_login(anon_client):
    response = anon_client.get(
        "/Search_job",
        params={"mine": "true"},
    )

    assert response.status_code == 401


def test_list_my_jobs_forbidden_for_freelancer(
    as_user,
    freelancer_user,
):
    c = as_user(freelancer_user)

    response = c.get(
        "/Search_job",
        params={"mine": "true"},
    )

    assert response.status_code == 403