from dataclasses import dataclass


@dataclass(frozen=True)
class SessionUser:
    user_id: int
    username: str | None
