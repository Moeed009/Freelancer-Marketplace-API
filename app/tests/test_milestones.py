
from app.models.contract import Contract
from app.models.enums import ContractStatus, MilestoneStatus
from app.models.job import Job, JobStatus, RateType
from app.models.milestone import Milestone
from app.models.proposal import Proposal, ProposalStatus
from app.models.user import User


def _make_contract(db, client: User, freelancer: User) -> Contract:
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
        status=ContractStatus.ACTIVE,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


def _make_milestone(db, contract: Contract, status=MilestoneStatus.PENDING) -> Milestone:
    milestone = Milestone(
        contract_id=contract.id,
        title="Design mockups",
        description="First milestone",
        amount=50,
        status=status,
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


def test_client_can_create_a_milestone(as_user, client_user, freelancer_user, db):
    contract = _make_contract(db, client_user, freelancer_user)
    c = as_user(client_user)

    response = c.post(
        "/Add a milestone",
        params={"contract_id": str(contract.id)},
        json={"title": "Design mockups", "amount": 50},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"
    assert response.json()["is_complete"] is False


def test_update_a_milestone_edits_pending_details(as_user, client_user, freelancer_user, db):
   
    contract = _make_contract(db, client_user, freelancer_user)
    milestone = _make_milestone(db, contract)
    c = as_user(client_user)

    response = c.patch(
        "/Update a milestone",
        params={"milestone_id": str(milestone.id)},
        json={"title": "Design mockups v2", "amount": 75},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Design mockups v2"
    assert body["amount"] == 75


def test_dedicated_status_endpoint_moves_submitted_to_approved(as_user, client_user, freelancer_user, db):
    contract = _make_contract(db, client_user, freelancer_user)
    milestone = _make_milestone(db, contract, status=MilestoneStatus.SUBMITTED)
    c = as_user(client_user)

    response = c.patch(
        "/Milestone Status",
        params={"milestone_id": str(milestone.id)},
        json={"status": "APPROVED"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["is_complete"] is True


def test_freelancer_cannot_approve_their_own_milestone(as_user, client_user, freelancer_user, db):
    contract = _make_contract(db, client_user, freelancer_user)
    milestone = _make_milestone(db, contract, status=MilestoneStatus.SUBMITTED)
    c = as_user(freelancer_user)

    response = c.patch(
        "/Milestone Status",
        params={"milestone_id": str(milestone.id)},
        json={"status": "APPROVED"},
    )

    assert response.status_code == 422  # invalid transition for this role


def test_delete_milestone_only_while_pending(as_user, client_user, freelancer_user, db):
    contract = _make_contract(db, client_user, freelancer_user)
    submitted_milestone = _make_milestone(db, contract, status=MilestoneStatus.SUBMITTED)
    c = as_user(client_user)

    response = c.delete("/Delete a milestone", params={"milestone_id": str(submitted_milestone.id)})

    assert response.status_code == 422
