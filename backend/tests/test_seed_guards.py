import pytest

from app import seed as seed_module


@pytest.mark.parametrize("mode", ["validate", "dry-run"])
def test_offline_seed_modes_never_construct_engine(monkeypatch, mode):
    monkeypatch.setattr("sys.argv", ["seed", "--mode", mode])

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected connection attempt")

    monkeypatch.setattr(seed_module, "create_database_engine", forbidden)
    seed_module.main()


def test_seed_import_refuses_before_constructing_engine(monkeypatch):
    monkeypatch.setattr("sys.argv", ["seed", "--mode", "import"])

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected connection attempt")

    monkeypatch.setattr(seed_module, "create_database_engine", forbidden)
    with pytest.raises(RuntimeError, match="Remote database writes are disabled"):
        seed_module.main()
