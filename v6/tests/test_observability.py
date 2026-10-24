
from app.observability.telemetry import observe_node


def test_observe_node_returns_function_result():
    @observe_node("test_node")
    def sample_node(value):
        return {"result": value + 1}

    assert sample_node(4) == {"result": 5}


def test_observe_node_preserves_exceptions():
    @observe_node("failing_test_node")
    def failing_node():
        raise ValueError("simulated failure")

    try:
        failing_node()
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == "simulated failure"
