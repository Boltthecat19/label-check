from labelcheck.rules.normalize import normalize, normalize_keep_case


def test_normalize_upper_and_punct():
    assert normalize("Stone’s  Throw,") == "STONES THROW"


def test_normalize_keeps_percent_and_dot():
    assert normalize("45% Alc./Vol.") == "45% ALC.VOL."


def test_keep_case_collapses_space_only():
    assert normalize_keep_case("GOVERNMENT   WARNING:\n(1) x") == "GOVERNMENT WARNING: (1) x"
