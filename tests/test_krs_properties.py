from hypothesis import given, settings, strategies as st

from app.services.krs_validators import (
    KRSContext,
    MAX_SKS,
    SKSValidator,
)


class DummyCourse:
    def __init__(self, kode_mk, sks):
        self.kode_mk = kode_mk
        self.nama = kode_mk
        self.sks = sks


class DummySession:
    pass


@given(
    existing_sks=st.lists(
        st.integers(min_value=1, max_value=4),
        max_size=30,
    ),
    new_sks=st.integers(min_value=1, max_value=4),
)
@settings(max_examples=100)
def test_property_total_sks_never_exceeds_24_when_accepted(
    existing_sks, new_sks
):
    existing_courses = [
        DummyCourse(f"MK{i}", sks)
        for i, sks in enumerate(existing_sks)
    ]
    new_course = DummyCourse("MK_NEW", new_sks)

    context = KRSContext(
        nim="20260010001",
        semester="20261",
        existing_courses=existing_courses,
        new_course=new_course,
        session=DummySession(),
    )

    result = SKSValidator().check(context)
    total_sks = sum(existing_sks) + new_sks

    assert result.oke == (total_sks <= MAX_SKS)

    if result.oke:
        assert total_sks <= MAX_SKS
    else:
        assert total_sks > MAX_SKS


@given(existing_count=st.integers(min_value=8, max_value=30))
@settings(max_examples=100)
def test_property_total_sks_above_24_is_always_rejected(existing_count):
    existing_courses = [
        DummyCourse(f"MK{i}", 3)
        for i in range(existing_count)
    ]
    new_course = DummyCourse("MK_NEW", 3)

    context = KRSContext(
        nim="20260010001",
        semester="20261",
        existing_courses=existing_courses,
        new_course=new_course,
        session=DummySession(),
    )

    result = SKSValidator().check(context)
    total_sks = (existing_count + 1) * 3

    assert result.oke is False
    assert total_sks > MAX_SKS
    assert str(total_sks) in result.message
