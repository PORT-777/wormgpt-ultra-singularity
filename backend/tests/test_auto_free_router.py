from model_catalog import ModelCatalogEntry, FreeType
from auto_free_router import select_model, VIRTUAL_MODEL_ID


def make_entry(mid, provider, caps, free_type=FreeType.FREE_FOREVER):
    return ModelCatalogEntry(model_id=mid, canonical_model_id=mid, provider_id=provider, capabilities=caps, free_type=free_type)


def test_resolve_basic():
    cat = [make_entry("m1", "groq", ["text", "streaming"]), make_entry("m2", "groq", ["text"])]
    r = select_model(cat, ["text", "streaming"])
    assert r is not None and r.model_id == "m1"


def test_no_candidate():
    cat = [make_entry("m1", "groq", ["text"])]
    r = select_model(cat, ["image"])
    assert r is None


def test_session_affinity():
    cat = [make_entry("m1", "groq", ["text"]), make_entry("m2", "groq", ["text"])]
    a = select_model(cat, ["text"], session_id="s1")
    b = select_model(cat, ["text"], session_id="s1")
    assert a.model_id == b.model_id


def test_paid_excluded():
    cat = [make_entry("m1", "groq", ["text"], free_type=FreeType.PAID)]
    r = select_model(cat, ["text"])
    assert r is None
