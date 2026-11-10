from __future__ import annotations

from collections.abc import Sequence

from langchain_core.messages import AIMessage, HumanMessage

from odrm.api.schemas import ChatMessage


def trim_history(
    messages: Sequence[ChatMessage],
    max_messages: int,
    max_chars: int,
) -> list[ChatMessage]:
    if not messages:
        return []

    newest_user_index = next(
        (index for index in range(len(messages) - 1, -1, -1) if messages[index].role == "user"),
        None,
    )

    kept_reversed: list[ChatMessage] = []
    total_chars = 0

    for index in range(len(messages) - 1, -1, -1):
        candidate = messages[index]
        within_count = len(kept_reversed) < max_messages
        within_chars = total_chars + len(candidate.content) <= max_chars
        if within_count and (within_chars or index == newest_user_index):
            kept_reversed.append(candidate)
            total_chars += len(candidate.content)

    return list(reversed(kept_reversed))


def normalize_history(messages: Sequence[ChatMessage]) -> list[ChatMessage]:
    first_user_index = next(
        (index for index, message in enumerate(messages) if message.role == "user"),
        None,
    )
    if first_user_index is None:
        return []

    normalized: list[ChatMessage] = []
    for candidate in messages[first_user_index:]:
        if normalized and normalized[-1].role == candidate.role:
            merged = f"{normalized[-1].content}\n\n{candidate.content}"
            normalized[-1] = ChatMessage(role=candidate.role, content=merged)
        else:
            normalized.append(candidate)
    return normalized


def to_langchain_messages(
    messages: Sequence[ChatMessage],
) -> list[HumanMessage | AIMessage]:
    return [
        HumanMessage(content=message.content)
        if message.role == "user"
        else AIMessage(content=message.content)
        for message in messages
    ]


def prepare_history(
    messages: Sequence[ChatMessage],
    max_messages: int,
    max_chars: int,
) -> list[HumanMessage | AIMessage]:
    trimmed = trim_history(messages, max_messages=max_messages, max_chars=max_chars)
    normalized = normalize_history(trimmed)
    return to_langchain_messages(normalized)
