

from app.models.contract import Contract
from app.models.enums import ContractStatus, JobStatus, MilestoneStatus, ProposalStatus, RateType
from app.models.job import Job
from app.models.milestone import Milestone
from app.models.proposal import Proposal
from app.models.user import User


def _make_contract(db, client: User, freelancer: User, status=ContractStatus.ACTIVE) -> Contract:
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


def test_list_my_contracts_only_shows_my_own(as_user, client_user, other_client_user, freelancer_user, db):
    mine = _make_contract(db, client_user, freelancer_user)
    _make_contract(db, other_client_user, freelancer_user)

    c = as_user(client_user)
    response = c.get("/List contracts")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(mine.id)]



def test_complete_contract_requires_all_milestones_approved(as_user, client_user, freelancer_user, db):
    contract = _make_contract(db, client_user, freelancer_user)
    db.add(Milestone(contract_id=contract.id, title="M1", amount=50, status=MilestoneStatus.PENDING))
    db.commit()

    c = as_user(client_user)
    response = c.patch(
        "/Contract Status",
        params={"contract_id": str(contract.id)},
        json={"status": "COMPLETED"},
    )

    assert response.status_code == 422


def test_cancel_contract_works_when_no_milestone_approved(as_user, client_user, freelancer_user, db):
   
    contract = _make_contract(db, client_user, freelancer_user)
    db.add(Milestone(contract_id=contract.id, title="M1", amount=50, status=MilestoneStatus.PENDING))
    db.commit()

    c = as_user(freelancer_user)  # either participant can cancel
    response = c.patch(
        "/Contract Status",
        params={"contract_id": str(contract.id)},
        json={"status": "CANCELLED"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_cancel_contract_blocked_once_a_milestone_is_approved(as_user, client_user, freelancer_user, db):
    contract = _make_contract(db, client_user, freelancer_user)
    db.add(Milestone(contract_id=contract.id, title="M1", amount=50, status=MilestoneStatus.APPROVED))
    db.commit()

    c = as_user(client_user)
    response = c.patch(
        "/Contract Status",
        params={"contract_id": str(contract.id)},
        json={"status": "CANCELLED"},
    )

    assert response.status_code == 422


def test_delete_contract_only_when_cancelled(as_user, client_user, freelancer_user, db):
    active_contract = _make_contract(db, client_user, freelancer_user, status=ContractStatus.ACTIVE)
    c = as_user(client_user)

    response = c.delete("/Delete a contract", params={"contract_id": str(active_contract.id)})
    assert response.status_code == 422

    cancelled_contract = _make_contract(db, client_user, freelancer_user, status=ContractStatus.CANCELLED)
    response = c.delete("/Delete a contract", params={"contract_id": str(cancelled_contract.id)})
    assert response.status_code == 204
