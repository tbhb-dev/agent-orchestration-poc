"""Example and property tests for plain bus subjects."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.subject import valid


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("a", True),
        ("a.b-2_c", True),
        ("a" * 255, True),
        ("", False),
        (".a", False),
        ("a.", False),
        ("a..b", False),
        ("a.*", False),
        ("a.>", False),
        ("a.B", False),
        ("a/b", False),
        ("é", False),
        ("\ud800", False),
        ("a" * 256, False),
    ],
)
def test_valid_examples(name: str, expected: bool) -> None:
    assert valid(name) is expected


@given(
    st.lists(st.from_regex(r"[a-z0-9_-]{1,12}", fullmatch=True), min_size=1, max_size=6)
)
def test_joined_plain_tokens_are_valid(tokens: list[str]) -> None:
    assert valid(".".join(tokens))


@given(
    st.from_regex(r"[a-z0-9_-]{1,12}", fullmatch=True),
    st.from_regex(r"[a-z0-9_-]{1,12}", fullmatch=True),
)
def test_empty_token_is_invalid(left: str, right: str) -> None:
    assert not valid(left + ".." + right)


@given(st.text(alphabet=st.characters(blacklist_categories=())))
def test_arbitrary_text_returns_bool(name: str) -> None:
    assert isinstance(valid(name), bool)
