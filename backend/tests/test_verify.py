from app.body_types import expected_body_type
from app.schemas import CarAttributes, SellerInput
from app.verify import verify


def seen(body="hatchback", colour="red", damages=(), body_conf=0.9):
    return CarAttributes.model_validate(
        {
            "make": None,
            "model": None,
            "body_type": body,
            "colour": colour,
            "damages": [
                {"type": t, "location": loc, "description": "x", "confidence": 0.9}
                for t, loc in damages
            ],
            "confidence": {
                "make": 0.9,
                "model": 0.9,
                "body_type": body_conf,
                "colour": 0.9,
            },
        }
    )


def seller(make="Maruti", model="Swift", colour=None, reported_damage=None):
    return SellerInput(
        registration_number="DL3CAB1234",
        make=make,
        model=model,
        year=2019,
        km_driven=40000,
        fuel_type="Petrol",
        transmission_type="Manual",
        colour=colour,
        reported_damage=reported_damage,
    )


def checks(flags):
    return {f["check"] for f in flags}


def test_body_type_lookup():
    assert expected_body_type("Swift") == "hatchback"
    assert expected_body_type("Swift Dzire VXI") == "sedan"
    assert expected_body_type("XUV700") == "suv"
    assert expected_body_type("Flying Car") is None


def test_honest_declaration_has_no_flags():
    assert verify(seller(), seen("hatchback")) == []


def test_wrong_body_type_is_flagged():
    flags = verify(seller(model="Creta"), seen("hatchback"))
    assert checks(flags) == {"body_type"}
    assert flags[0]["severity"] == "high"


def test_suv_muv_mixup_is_not_flagged():
    assert verify(seller(model="Ertiga"), seen("suv")) == []


def test_low_confidence_photo_is_not_flagged():
    assert verify(seller(model="Creta"), seen("hatchback", body_conf=0.5)) == []


def test_unknown_model_gets_catalog_flag():
    assert checks(verify(seller(model="Flying Car"), seen())) == {"catalog"}


def test_grey_silver_is_compatible():
    assert verify(seller(colour="grey"), seen(colour="silver")) == []


def test_undeclared_damage_is_flagged():
    flags = verify(seller(reported_damage=False), seen(damages=[("dent", "bonnet")]))
    assert checks(flags) == {"damage"}
