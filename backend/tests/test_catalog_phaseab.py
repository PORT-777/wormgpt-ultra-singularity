import pytest
from model_catalog import ModelCatalogEntry, FreeType
from free_eligibility import classify_free_type


def test_all_freetypes():
    for ft in FreeType:
        assert ft.value == ft.value


def test_classify_paid():
    assert classify_free_type({"paid": True}) == FreeType.PAID


def test_classify_unknown():
    assert classify_free_type({}) == FreeType.UNKNOWN


def test_classify_recurring():
    assert classify_free_type({"recurring_free": True}) == FreeType.RECURRING_FREE_TIER


def test_classify_forever():
    assert classify_free_type({"free_forever": True}) == FreeType.FREE_FOREVER


def test_classify_one_time():
    assert classify_free_type({"one_time_credit": True}) == FreeType.ONE_TIME_INITIAL


def test_classify_promo():
    assert classify_free_type({"temporary_promo": True}) == FreeType.TEMPORARY_PROMOTION


def test_classify_discontinued():
    assert classify_free_type({"discontinued": True}) == FreeType.DISCONTINUED


def test_entry_validation():
    e = ModelCatalogEntry(model_id="m", canonical_model_id="m", provider_id="groq")
    assert e.free_type == FreeType.UNKNOWN


def test_entry_invalid_missing():
    with pytest.raises(Exception):
        ModelCatalogEntry()  # type: ignore
