from app import should_autofill_field


def test_should_autofill_field_overwrites_when_preserve_disabled():
    assert should_autofill_field("valor", False) is True


def test_should_autofill_field_skips_when_preserve_enabled_with_text():
    assert should_autofill_field("valor", True) is False


def test_should_autofill_field_allows_blank_strings():
    assert should_autofill_field("   ", True) is True
    assert should_autofill_field("", True) is True


def test_should_autofill_field_accepts_none_values():
    assert should_autofill_field(None, True) is True
