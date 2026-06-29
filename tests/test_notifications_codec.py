from custom_components.plant_care_scheduler.notifications import encode_action, decode_action


def test_roundtrip():
    p = encode_action("01ABC", "water")
    assert p == "pcs::01ABC::water"
    assert decode_action(p) == ("01ABC", "water")


def test_decode_rejects_garbage():
    assert decode_action("nope") is None
    assert decode_action("pcs::x::flying") is None
    assert decode_action("") is None
    assert decode_action(None) is None
