from enum import Enum


class OpenAIEnums(str, Enum):
    ROLE_SYSTEM = "system"
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
