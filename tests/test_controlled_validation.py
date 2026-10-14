import pytest

from validation import controlled_windows


def test_controlled_harness_refuses_local_execution_before_native_access(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    def forbidden(*args, **kwargs):
        pytest.fail("Lab accessed native state before refusing normal-host execution")

    monkeypatch.setattr(controlled_windows, "native", forbidden)
    with pytest.raises(RuntimeError, match="REFUSED"):
        controlled_windows.main(["--disposable-github-runner"])


def test_registry_acl_restoration_requires_verified_readback(monkeypatch):
    monkeypatch.setattr(controlled_windows, "set_registry_acl", lambda original: None)
    monkeypatch.setattr(controlled_windows, "read_registry_acl", lambda: "unexpected-descriptor")
    with pytest.raises(RuntimeError, match="Registry ACL rollback readback mismatch"):
        controlled_windows.restore_registry_acl("original-descriptor")
