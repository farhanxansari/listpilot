from app.tools import (
    MileageArgs,
    ValidateRegistrationArgs,
    _match_category,
    check_mileage,
    validate_registration,
)


def reg(n):
    return validate_registration(ValidateRegistrationArgs(registration_number=n), None)


def mil(year, km):
    return check_mileage(MileageArgs(year=year, km_driven=km), None)["verdict"]


def test_standard_registration():
    r = reg("DL 3C AB 1234")
    assert r["valid"]
    assert r["state"] == "Delhi"


def test_registration_without_spaces():
    r = reg("hr26dk8337")
    assert r["valid"]
    assert r["state"] == "Haryana"


def test_bh_series():
    assert reg("22 BH 1234 AA")["series"] == "BH"


def test_invalid_registration():
    assert not reg("XYZ123")["valid"]
    assert not reg("ZZ 01 AB 1234")["valid"]


def test_mileage_verdicts():
    assert mil(2018, 3000) == "suspiciously_low"
    assert mil(2024, 200_000) == "very_high"
    assert mil(2020, 60_000) == "normal"


def test_category_case_insensitive():
    assert _match_category("cng", "fuel_type") == "CNG"
    assert _match_category("AUTOMATIC", "transmission_type") == "Automatic"
