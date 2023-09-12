from typing import List

from pydantic import Field

from agentverse.message import Message

from . import memory_registry
from .base import BaseMemory


@memory_registry.register("chat_history")
class ChatHistoryMemory(BaseMemory):
    messages: List[Message] = Field(default=[])

    def add_message(self, messages: List[Message]) -> None:
        for message in messages:
            self.messages.append(message)

    def to_string(self, add_sender_prefix: bool = False) -> str:
        if add_sender_prefix:
            return "\n".join(
                [
                    f"[{message.sender}]: {message.content}"
                    if message.sender != ""
                    else message.content
                    for message in self.messages
                ]
            )
        else:
            return "\n".join([message.content for message in self.messages])

    def to_messages(self, my_name: str = "", start_index: int = 0) -> List[dict]:
        messages = []
        for message in self.messages[start_index:]:
            messages.append(
                {
                    "role": "user" if message.sender != my_name else "assistant",
                    "content": f"[{message.sender}]: {message.content}",
                }
            )
        return messages

    def reset(self) -> None:
        self.messages = []
