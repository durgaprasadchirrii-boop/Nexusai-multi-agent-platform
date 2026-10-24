
import operator
from typing import Annotated, TypedDict, Any


class NexusState(TypedDict):
    user_request: str
    objective: str
    tasks: list[dict[str, Any]]

    results: Annotated[list[dict[str, Any]], operator.add]
    execution_log: Annotated[list[dict[str, Any]], operator.add]

    final_report: str
    status: str

    # V4 verification
    review: dict[str, Any]
    revision_count: int
    verification_status: str
    unresolved_issues: list[str]

    # V4 approval
    approval_required: bool
    approval_status: str
    approval_comment: str


class TaskInput(TypedDict):
    user_request: str
    task: dict[str, Any]
