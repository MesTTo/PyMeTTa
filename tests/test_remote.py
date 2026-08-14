"""Purpose: verify the remote transport's boundary and authorization policy.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from petta import remote


def test_bearer_token_uses_constant_time_comparison(monkeypatch):
    calls = []
    policies = []

    def compare(supplied, expected):
        calls.append((supplied, expected))
        return supplied == expected

    def authorize(headers):
        policies.append(headers)
        return True

    monkeypatch.setattr(remote.hmac, "compare_digest", compare)

    matching = {"authorization": "Bearer secret"}
    assert remote._is_authorized(matching, "secret", authorize)
    assert not remote._is_authorized(
        {"authorization": "Bearer wrong"}, "secret", authorize
    )
    assert not remote._is_authorized({}, "secret", authorize)

    assert calls == [
        ("Bearer secret", "Bearer secret"),
        ("Bearer wrong", "Bearer secret"),
        ("", "Bearer secret"),
    ]
    assert policies == [matching]
