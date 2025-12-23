from utils.technical_key import EMPTY_PART, build_technical_key, iter_technical_keys


def test_build_technical_key_normalizes_and_fills_placeholders():
    key = build_technical_key(
        "2025-0001",
        "prod-1",
        "",
        "t12345",
        "2025-01-01",
        "",
    )
    assert key == (
        "2025-0001",
        "PROD-1",
        EMPTY_PART,
        "T12345",
        "2025-01-01",
        EMPTY_PART,
    )


def test_iter_technical_keys_cartesian_expansion():
    keys = list(
        iter_technical_keys(
            "2025-0001",
            "prod-1",
            ["c1", "c2"],
            ["t1"],
            "2025-01-01",
            ["c00000001", ""],
        )
    )
    assert keys == [
        ("2025-0001", "PROD-1", "C1", "T1", "2025-01-01", "C00000001"),
        ("2025-0001", "PROD-1", "C1", "T1", "2025-01-01", EMPTY_PART),
        ("2025-0001", "PROD-1", "C2", "T1", "2025-01-01", "C00000001"),
        ("2025-0001", "PROD-1", "C2", "T1", "2025-01-01", EMPTY_PART),
    ]
