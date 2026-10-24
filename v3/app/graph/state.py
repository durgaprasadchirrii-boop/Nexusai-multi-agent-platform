
import operator
from typing import Annotated, TypedDict


class NexusState(TypedDict):
    user_request: str
    objective: str
    tasks: list[dict]

    # Parallel workers append their individual results.
    results: Annotated[list[dict], operator.add]

    # Each worker contributes its execution trace.
    execution_log: Annotated[list[dict], operator.add]

    final_report: str
    status: str


class TaskInput(TypedDict):
    user_request: str
    task: dict
