"""Queue name registry tests."""

from porterchain_shared.queue.names import QueueName


def test_redis_keys_are_namespaced() -> None:
    for queue in QueueName:
        assert queue.redis_key.startswith("porterchain:queue:")


def test_all_queues_have_processors() -> None:
    expected = {"emails", "sms", "push", "dispatch", "routing", "billing", "reports", "webhooks", "notify_fast", "notify_slow"}
    assert {q.value for q in QueueName} == expected
