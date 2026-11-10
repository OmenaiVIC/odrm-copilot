from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from odrm.agents.context import (
    normalize_history,
    prepare_history,
    to_langchain_messages,
    trim_history,
)
from odrm.api.schemas import ChatMessage


def message(role: str, content: str) -> ChatMessage:
    return ChatMessage(role=role, content=content)  # type: ignore[arg-type]


def test_trim_history_keeps_everything_when_both_budgets_are_sufficient() -> None:
    messages = [
        message("user", "first"),
        message("assistant", "reply"),
        message("user", "second"),
    ]

    assert trim_history(messages, max_messages=10, max_chars=1_000) == messages


def test_trim_history_drops_the_oldest_messages_when_the_count_budget_is_exceeded() -> None:
    messages = [
        message("user", "first"),
        message("assistant", "reply"),
        message("user", "second"),
    ]

    assert trim_history(messages, max_messages=2, max_chars=1_000) == [
        message("assistant", "reply"),
        message("user", "second"),
    ]


def test_trim_history_drops_the_oldest_messages_when_the_character_budget_is_exceeded() -> None:
    messages = [
        message("user", "first"),
        message("assistant", "reply"),
        message("user", "second"),
    ]

    assert trim_history(messages, max_messages=10, max_chars=11) == [
        message("assistant", "reply"),
        message("user", "second"),
    ]


def test_trim_history_always_keeps_the_newest_user_message() -> None:
    messages = [message("assistant", "reply"), message("user", "a long request")]

    assert trim_history(messages, max_messages=10, max_chars=1) == [
        message("user", "a long request")
    ]


def test_trim_history_returns_an_empty_list_for_empty_input() -> None:
    assert trim_history([], max_messages=10, max_chars=1_000) == []


def test_normalize_history_drops_a_leading_assistant_message() -> None:
    messages = [
        message("assistant", "orphaned reply"),
        message("user", "question"),
        message("assistant", "answer"),
    ]

    assert normalize_history(messages) == [
        message("user", "question"),
        message("assistant", "answer"),
    ]


def test_normalize_history_merges_consecutive_same_role_messages() -> None:
    messages = [
        message("user", "first"),
        message("user", "second"),
        message("assistant", "reply one"),
        message("assistant", "reply two"),
    ]

    assert normalize_history(messages) == [
        message("user", "first\n\nsecond"),
        message("assistant", "reply one\n\nreply two"),
    ]


def test_normalize_history_returns_an_empty_list_when_only_assistant_messages_exist() -> None:
    assert normalize_history([message("assistant", "reply")]) == []


def test_to_langchain_messages_converts_roles_in_order() -> None:
    messages = [
        message("user", "question"),
        message("assistant", "answer"),
        message("user", "follow-up"),
    ]

    converted = to_langchain_messages(messages)

    assert len(converted) == 3
    assert isinstance(converted[0], HumanMessage)
    assert converted[0].content == "question"
    assert isinstance(converted[1], AIMessage)
    assert converted[1].content == "answer"
    assert isinstance(converted[2], HumanMessage)
    assert converted[2].content == "follow-up"


def test_prepare_history_composes_trim_normalize_and_convert() -> None:
    messages = [
        message("assistant", "orphaned reply"),
        message("user", "first question"),
        message("assistant", "first answer"),
        message("user", "second question"),
    ]

    prepared = prepare_history(messages, max_messages=3, max_chars=1_000)

    assert len(prepared) == 3
    assert isinstance(prepared[0], HumanMessage)
    assert prepared[0].content == "first question"
    assert isinstance(prepared[1], AIMessage)
    assert prepared[1].content == "first answer"
    assert isinstance(prepared[2], HumanMessage)
    assert prepared[2].content == "second question"
