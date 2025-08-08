from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CreateCharacterRequest(_message.Message):
    __slots__ = ("name", "vocation")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VOCATION_FIELD_NUMBER: _ClassVar[int]
    name: str
    vocation: str
    def __init__(self, name: _Optional[str] = ..., vocation: _Optional[str] = ...) -> None: ...

class CreateCharacterResponse(_message.Message):
    __slots__ = ("success", "message", "player")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    PLAYER_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    player: PlayerInfo
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., player: _Optional[_Union[PlayerInfo, _Mapping]] = ...) -> None: ...

class ListCharactersRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListCharactersResponse(_message.Message):
    __slots__ = ("players",)
    PLAYERS_FIELD_NUMBER: _ClassVar[int]
    players: _containers.RepeatedCompositeFieldContainer[PlayerInfo]
    def __init__(self, players: _Optional[_Iterable[_Union[PlayerInfo, _Mapping]]] = ...) -> None: ...

class JoinWorldRequest(_message.Message):
    __slots__ = ("player_id",)
    PLAYER_ID_FIELD_NUMBER: _ClassVar[int]
    player_id: str
    def __init__(self, player_id: _Optional[str] = ...) -> None: ...

class JoinWorldResponse(_message.Message):
    __slots__ = ("success", "message", "player", "other_players")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    PLAYER_FIELD_NUMBER: _ClassVar[int]
    OTHER_PLAYERS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    player: PlayerInfo
    other_players: _containers.RepeatedCompositeFieldContainer[PlayerInfo]
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., player: _Optional[_Union[PlayerInfo, _Mapping]] = ..., other_players: _Optional[_Iterable[_Union[PlayerInfo, _Mapping]]] = ...) -> None: ...

class PlayerMoveRequest(_message.Message):
    __slots__ = ("target_x", "target_y", "movement_type")
    TARGET_X_FIELD_NUMBER: _ClassVar[int]
    TARGET_Y_FIELD_NUMBER: _ClassVar[int]
    MOVEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    target_x: float
    target_y: float
    movement_type: str
    def __init__(self, target_x: _Optional[float] = ..., target_y: _Optional[float] = ..., movement_type: _Optional[str] = ...) -> None: ...

class PlayerMoveResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class WorldUpdateRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class WorldUpdateResponse(_message.Message):
    __slots__ = ("players", "timestamp")
    PLAYERS_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    players: _containers.RepeatedCompositeFieldContainer[PlayerInfo]
    timestamp: int
    def __init__(self, players: _Optional[_Iterable[_Union[PlayerInfo, _Mapping]]] = ..., timestamp: _Optional[int] = ...) -> None: ...

class PlayerActionRequest(_message.Message):
    __slots__ = ("action_type", "target_id", "parameters")
    class ParametersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ACTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    TARGET_ID_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    action_type: str
    target_id: str
    parameters: _containers.ScalarMap[str, str]
    def __init__(self, action_type: _Optional[str] = ..., target_id: _Optional[str] = ..., parameters: _Optional[_Mapping[str, str]] = ...) -> None: ...

class PlayerActionResponse(_message.Message):
    __slots__ = ("success", "message", "affected_players")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    AFFECTED_PLAYERS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    affected_players: _containers.RepeatedCompositeFieldContainer[PlayerInfo]
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., affected_players: _Optional[_Iterable[_Union[PlayerInfo, _Mapping]]] = ...) -> None: ...

class GetWorldStateRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetWorldStateResponse(_message.Message):
    __slots__ = ("players", "timestamp")
    PLAYERS_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    players: _containers.RepeatedCompositeFieldContainer[PlayerInfo]
    timestamp: int
    def __init__(self, players: _Optional[_Iterable[_Union[PlayerInfo, _Mapping]]] = ..., timestamp: _Optional[int] = ...) -> None: ...

class PlayerInfo(_message.Message):
    __slots__ = ("id", "name", "vocation", "experience", "level", "position_x", "position_y", "current_hp", "max_hp", "current_mp", "max_mp", "attack", "defense", "speed", "movement_state", "facing_direction", "is_online")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    VOCATION_FIELD_NUMBER: _ClassVar[int]
    EXPERIENCE_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    POSITION_X_FIELD_NUMBER: _ClassVar[int]
    POSITION_Y_FIELD_NUMBER: _ClassVar[int]
    CURRENT_HP_FIELD_NUMBER: _ClassVar[int]
    MAX_HP_FIELD_NUMBER: _ClassVar[int]
    CURRENT_MP_FIELD_NUMBER: _ClassVar[int]
    MAX_MP_FIELD_NUMBER: _ClassVar[int]
    ATTACK_FIELD_NUMBER: _ClassVar[int]
    DEFENSE_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    MOVEMENT_STATE_FIELD_NUMBER: _ClassVar[int]
    FACING_DIRECTION_FIELD_NUMBER: _ClassVar[int]
    IS_ONLINE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    vocation: str
    experience: int
    level: int
    position_x: float
    position_y: float
    current_hp: int
    max_hp: int
    current_mp: int
    max_mp: int
    attack: int
    defense: int
    speed: float
    movement_state: str
    facing_direction: int
    is_online: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., vocation: _Optional[str] = ..., experience: _Optional[int] = ..., level: _Optional[int] = ..., position_x: _Optional[float] = ..., position_y: _Optional[float] = ..., current_hp: _Optional[int] = ..., max_hp: _Optional[int] = ..., current_mp: _Optional[int] = ..., max_mp: _Optional[int] = ..., attack: _Optional[int] = ..., defense: _Optional[int] = ..., speed: _Optional[float] = ..., movement_state: _Optional[str] = ..., facing_direction: _Optional[int] = ..., is_online: bool = ...) -> None: ...
