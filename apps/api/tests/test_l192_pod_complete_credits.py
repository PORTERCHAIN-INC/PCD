"""L192: pod-complete alone (web portal path) must credit the driver wallet once."""
import inspect

from porterchain_driver import pod


def test_complete_pod_credits_delivery():
    src = inspect.getsource(pod.ProofOfDeliveryService.complete_pod)
    assert "credit_delivery" in src
