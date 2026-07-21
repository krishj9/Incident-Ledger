from typing import NamedTuple

from app.domain.enums import IncidentStatus


class InvalidTransition(Exception):
    pass


class Transition(NamedTuple):
    from_status: IncidentStatus
    command: str
    to_status: IncidentStatus
    allowed_roles: set[str]


# Commands
CMD_SUBMIT = "submit"
CMD_ACK_REVIEW = "acknowledge_review"
CMD_REQ_CHANGES = "request_changes"
CMD_UPDATE_SUBMIT = "update_and_submit"
CMD_APPROVE = "approve"
CMD_ACK_GUARDIAN = "acknowledge_guardian"
CMD_DISAGREE_GUARDIAN = "disagree_guardian"
CMD_CLOSE_UNREACHABLE = "close_unreachable"
CMD_CLOSE = "close"
CMD_CREATE_ADDENDUM = "create_addendum"

_DIRECTOR_ROLES = {"director", "backup_director", "regional_admin", "compliance_reviewer"}

TRANSITIONS: list[Transition] = [
    # Draft
    Transition(IncidentStatus.draft, CMD_SUBMIT, IncidentStatus.submitted, {"staff"}),
    
    # Submitted
    Transition(IncidentStatus.submitted, CMD_ACK_REVIEW, IncidentStatus.under_review, _DIRECTOR_ROLES),
    Transition(IncidentStatus.submitted, CMD_REQ_CHANGES, IncidentStatus.changes_requested, _DIRECTOR_ROLES),
    
    # Under review
    Transition(IncidentStatus.under_review, CMD_REQ_CHANGES, IncidentStatus.changes_requested, _DIRECTOR_ROLES),
    Transition(IncidentStatus.under_review, CMD_APPROVE, IncidentStatus.guardian_ack_pending, _DIRECTOR_ROLES),
    
    # Changes requested
    Transition(IncidentStatus.changes_requested, CMD_UPDATE_SUBMIT, IncidentStatus.submitted, {"staff"}),
    
    # Guardian ack pending
    Transition(IncidentStatus.guardian_ack_pending, CMD_ACK_GUARDIAN, IncidentStatus.acknowledged, {"guardian", "staff"}),
    Transition(IncidentStatus.guardian_ack_pending, CMD_DISAGREE_GUARDIAN, IncidentStatus.acknowledged, {"guardian", "staff"}),
    Transition(IncidentStatus.guardian_ack_pending, CMD_CLOSE_UNREACHABLE, IncidentStatus.ack_unreachable, _DIRECTOR_ROLES),
    
    # Closing
    Transition(IncidentStatus.acknowledged, CMD_CLOSE, IncidentStatus.closed, _DIRECTOR_ROLES | {"system"}),
    Transition(IncidentStatus.ack_unreachable, CMD_CLOSE, IncidentStatus.closed, _DIRECTOR_ROLES | {"system"}),
]

def transition(current_status: IncidentStatus, command: str, actor_role: str) -> IncidentStatus:
    """
    Apply a state machine transition.
    Raises InvalidTransition if the transition is invalid or the actor is unauthorized.
    """
    # Note: create_addendum is a special command that doesn't change the main report's status
    # but creates a new addendum draft. Valid from approved, acknowledged, ack_unreachable, closed.
    if command == CMD_CREATE_ADDENDUM:
        if current_status not in (
            IncidentStatus.approved,
            IncidentStatus.guardian_ack_pending,
            IncidentStatus.acknowledged,
            IncidentStatus.ack_unreachable,
            IncidentStatus.closed,
        ):
            raise InvalidTransition(f"Cannot create addendum from status {current_status.value}")
        if actor_role not in {"staff"} | _DIRECTOR_ROLES:
            raise InvalidTransition(f"Role {actor_role} not authorized for {command}")
        return current_status  # Does not change the main report's status natively here
    
    for t in TRANSITIONS:
        if t.from_status == current_status and t.command == command:
            if actor_role not in t.allowed_roles:
                raise InvalidTransition(f"Role {actor_role} not authorized for command {command}")
            return t.to_status

    raise InvalidTransition(f"Invalid transition from {current_status.value} via {command}")
