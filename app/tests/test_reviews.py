from app.models.contract import Contract
from app.models.enums import (
    ContractStatus,
    JobStatus,
    ProposalStatus,
    RateType,
)
from app.models.job import Job
from app.models.proposal import Proposal
from app.models.user import User


def _make_contract(
    db,
    client: User,
    freelancer: User,
    status=ContractStatus.COMPLETED,
) -> Contract:
    job = Job(
        client_id=client.id,
        title="Website",
        description="desc",
        rate_type=RateType.FIXED,
        budget_min=100,
        budget_max=100,
        status=JobStatus.CLOSED,
    )

    db.add(job)
    db.flush()

    proposal = Proposal(
        job_id=job.id,
        freelancer_id=freelancer.id,
        cover_letter="I can do this.",
        bid_amount=100,
        estimated_duration_days=5,
        status=ProposalStatus.ACCEPTED,
    )

    db.add(proposal)
    db.flush()

    contract = Contract(
        job_id=job.id,
        proposal_id=proposal.id,
        client_id=client.id,
        freelancer_id=freelancer.id,
        agreed_amount=100,
        status=status,
    )

    db.add(contract)
    db.commit()
    db.refresh(contract)

    return contract


def test_cannot_review_before_contract_completed(
    as_user,
    client_user,
    freelancer_user,
    db,
):
    contract = _make_contract(
        db,
        client_user,
        freelancer_user,
        status=ContractStatus.ACTIVE,
    )

    c = as_user(client_user)

    response = c.post(
        "/Post_Reviews",
        params={"contract_id": str(contract.id)},
        json={
            "rating": 5,
            "comment": "Great work",
        },
    )

    assert response.status_code == 422


def test_client_can_review_freelancer_after_completion(
    as_user,
    client_user,
    freelancer_user,
    db,
):
    contract = _make_contract(
        db,
        client_user,
        freelancer_user,
    )

    c = as_user(client_user)

    response = c.post(
        "/Post_Reviews",
        params={"contract_id": str(contract.id)},
        json={
            "rating": 5,
            "comment": "Great work",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["reviewer_id"] == str(client_user.id)
    assert body["reviewee_id"] == str(freelancer_user.id)


def test_cannot_review_the_same_contract_twice(
    as_user,
    client_user,
    freelancer_user,
    db,
):
    contract = _make_contract(
        db,
        client_user,
        freelancer_user,
    )

    c = as_user(client_user)

    first = c.post(
        "/Post_Reviews",
        params={"contract_id": str(contract.id)},
        json={"rating": 5},
    )

    assert first.status_code == 201

    second = c.post(
        "/Post_Reviews",
        params={"contract_id": str(contract.id)},
        json={"rating": 4},
    )

    assert second.status_code == 409


def test_only_the_reviewer_can_edit_their_review(
    as_user,
    client_user,
    freelancer_user,
    db,
):
    contract = _make_contract(
        db,
        client_user,
        freelancer_user,
    )

    reviewer_client = as_user(client_user)

    created_response = reviewer_client.post(
        "/Post_Reviews",
        params={"contract_id": str(contract.id)},
        json={"rating": 3},
    )

    assert created_response.status_code == 201

    created = created_response.json()

    reviewee_client = as_user(freelancer_user)

    response = reviewee_client.patch(
        "/Update_review",
        params={"review_id": created["id"]},
        json={"rating": 1},
    )

    assert response.status_code == 403

    response = reviewer_client.patch(
        "/Update_review",
        params={"review_id": created["id"]},
        json={
            "rating": 4,
            "comment": "Updated",
        },
    )

    assert response.status_code == 200
    assert response.json()["rating"] == 4


def test_only_the_reviewer_can_delete_their_review(
    as_user,
    client_user,
    freelancer_user,
    db,
):
    contract = _make_contract(
        db,
        client_user,
        freelancer_user,
    )

    reviewer_client = as_user(client_user)

    created_response = reviewer_client.post(
        "/Post_Reviews",
        params={"contract_id": str(contract.id)},
        json={"rating": 5},
    )

    assert created_response.status_code == 201

    created = created_response.json()

    reviewee_client = as_user(freelancer_user)

    response = reviewee_client.delete(
        "/Delete_review",
        params={"review_id": created["id"]},
    )

    assert response.status_code == 403

    response = reviewer_client.delete(
        "/Delete_review",
        params={"review_id": created["id"]},
    )

    assert response.status_code == 204