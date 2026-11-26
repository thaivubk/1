from vpak.catalog import AGENTS, ROOMS


def test_catalog_consistent():
    room_ids = {r["id"] for r in ROOMS}
    assert len(AGENTS) == 13 and all(a["room"] in room_ids for a in AGENTS.values())


def test_room_colors():
    assert [(r["id"], r["color"]) for r in ROOMS] == [
        ("tt", "#0F766E"), ("qt", "#6D28D9"), ("sx", "#BE185D"),
        ("dp", "#1F3A5F"), ("qd", "#92400E"), ("cd", "#4D7C0F")]
