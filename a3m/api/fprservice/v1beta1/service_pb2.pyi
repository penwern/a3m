from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GetRegistryRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetRegistryResponse(_message.Message):
    __slots__ = ("schema_version", "source_sha256", "a3m_version", "instance_id", "groups", "formats", "versions", "tools", "commands", "rules", "diagnostics")
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_SHA256_FIELD_NUMBER: _ClassVar[int]
    A3M_VERSION_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    FORMATS_FIELD_NUMBER: _ClassVar[int]
    VERSIONS_FIELD_NUMBER: _ClassVar[int]
    TOOLS_FIELD_NUMBER: _ClassVar[int]
    COMMANDS_FIELD_NUMBER: _ClassVar[int]
    RULES_FIELD_NUMBER: _ClassVar[int]
    DIAGNOSTICS_FIELD_NUMBER: _ClassVar[int]
    schema_version: int
    source_sha256: str
    a3m_version: str
    instance_id: str
    groups: _containers.RepeatedCompositeFieldContainer[FormatGroup]
    formats: _containers.RepeatedCompositeFieldContainer[Format]
    versions: _containers.RepeatedCompositeFieldContainer[FormatVersion]
    tools: _containers.RepeatedCompositeFieldContainer[Tool]
    commands: _containers.RepeatedCompositeFieldContainer[Command]
    rules: _containers.RepeatedCompositeFieldContainer[Rule]
    diagnostics: _containers.RepeatedCompositeFieldContainer[Diagnostic]
    def __init__(self, schema_version: _Optional[int] = ..., source_sha256: _Optional[str] = ..., a3m_version: _Optional[str] = ..., instance_id: _Optional[str] = ..., groups: _Optional[_Iterable[_Union[FormatGroup, _Mapping]]] = ..., formats: _Optional[_Iterable[_Union[Format, _Mapping]]] = ..., versions: _Optional[_Iterable[_Union[FormatVersion, _Mapping]]] = ..., tools: _Optional[_Iterable[_Union[Tool, _Mapping]]] = ..., commands: _Optional[_Iterable[_Union[Command, _Mapping]]] = ..., rules: _Optional[_Iterable[_Union[Rule, _Mapping]]] = ..., diagnostics: _Optional[_Iterable[_Union[Diagnostic, _Mapping]]] = ...) -> None: ...

class FormatGroup(_message.Message):
    __slots__ = ("uuid", "slug", "description", "source_index")
    UUID_FIELD_NUMBER: _ClassVar[int]
    SLUG_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_INDEX_FIELD_NUMBER: _ClassVar[int]
    uuid: str
    slug: str
    description: str
    source_index: int
    def __init__(self, uuid: _Optional[str] = ..., slug: _Optional[str] = ..., description: _Optional[str] = ..., source_index: _Optional[int] = ...) -> None: ...

class Format(_message.Message):
    __slots__ = ("uuid", "slug", "description", "group", "source_index")
    UUID_FIELD_NUMBER: _ClassVar[int]
    SLUG_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    GROUP_FIELD_NUMBER: _ClassVar[int]
    SOURCE_INDEX_FIELD_NUMBER: _ClassVar[int]
    uuid: str
    slug: str
    description: str
    group: str
    source_index: int
    def __init__(self, uuid: _Optional[str] = ..., slug: _Optional[str] = ..., description: _Optional[str] = ..., group: _Optional[str] = ..., source_index: _Optional[int] = ...) -> None: ...

class FormatVersion(_message.Message):
    __slots__ = ("uuid", "slug", "description", "format", "version", "pronom_id", "enabled", "replaces", "lastmodified", "access_format", "preservation_format", "source_index", "active", "resolves_pronom_id")
    UUID_FIELD_NUMBER: _ClassVar[int]
    SLUG_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    PRONOM_ID_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    REPLACES_FIELD_NUMBER: _ClassVar[int]
    LASTMODIFIED_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FORMAT_FIELD_NUMBER: _ClassVar[int]
    PRESERVATION_FORMAT_FIELD_NUMBER: _ClassVar[int]
    SOURCE_INDEX_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    RESOLVES_PRONOM_ID_FIELD_NUMBER: _ClassVar[int]
    uuid: str
    slug: str
    description: str
    format: str
    version: str
    pronom_id: str
    enabled: bool
    replaces: str
    lastmodified: str
    access_format: bool
    preservation_format: bool
    source_index: int
    active: bool
    resolves_pronom_id: bool
    def __init__(self, uuid: _Optional[str] = ..., slug: _Optional[str] = ..., description: _Optional[str] = ..., format: _Optional[str] = ..., version: _Optional[str] = ..., pronom_id: _Optional[str] = ..., enabled: bool = ..., replaces: _Optional[str] = ..., lastmodified: _Optional[str] = ..., access_format: bool = ..., preservation_format: bool = ..., source_index: _Optional[int] = ..., active: bool = ..., resolves_pronom_id: bool = ...) -> None: ...

class Tool(_message.Message):
    __slots__ = ("uuid", "slug", "description", "version", "enabled", "source_index")
    UUID_FIELD_NUMBER: _ClassVar[int]
    SLUG_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    SOURCE_INDEX_FIELD_NUMBER: _ClassVar[int]
    uuid: str
    slug: str
    description: str
    version: str
    enabled: bool
    source_index: int
    def __init__(self, uuid: _Optional[str] = ..., slug: _Optional[str] = ..., description: _Optional[str] = ..., version: _Optional[str] = ..., enabled: bool = ..., source_index: _Optional[int] = ...) -> None: ...

class Command(_message.Message):
    __slots__ = ("uuid", "description", "tool", "enabled", "replaces", "lastmodified", "command", "command_usage", "script_type", "output_location", "output_format", "verification_command", "event_detail_command", "source_index")
    UUID_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    TOOL_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    REPLACES_FIELD_NUMBER: _ClassVar[int]
    LASTMODIFIED_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    COMMAND_USAGE_FIELD_NUMBER: _ClassVar[int]
    SCRIPT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_LOCATION_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FORMAT_FIELD_NUMBER: _ClassVar[int]
    VERIFICATION_COMMAND_FIELD_NUMBER: _ClassVar[int]
    EVENT_DETAIL_COMMAND_FIELD_NUMBER: _ClassVar[int]
    SOURCE_INDEX_FIELD_NUMBER: _ClassVar[int]
    uuid: str
    description: str
    tool: str
    enabled: bool
    replaces: str
    lastmodified: str
    command: str
    command_usage: str
    script_type: str
    output_location: str
    output_format: str
    verification_command: str
    event_detail_command: str
    source_index: int
    def __init__(self, uuid: _Optional[str] = ..., description: _Optional[str] = ..., tool: _Optional[str] = ..., enabled: bool = ..., replaces: _Optional[str] = ..., lastmodified: _Optional[str] = ..., command: _Optional[str] = ..., command_usage: _Optional[str] = ..., script_type: _Optional[str] = ..., output_location: _Optional[str] = ..., output_format: _Optional[str] = ..., verification_command: _Optional[str] = ..., event_detail_command: _Optional[str] = ..., source_index: _Optional[int] = ...) -> None: ...

class Rule(_message.Message):
    __slots__ = ("uuid", "format", "command", "purpose", "enabled", "replaces", "lastmodified", "source_index", "selected_by_registry", "loaded")
    UUID_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    PURPOSE_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    REPLACES_FIELD_NUMBER: _ClassVar[int]
    LASTMODIFIED_FIELD_NUMBER: _ClassVar[int]
    SOURCE_INDEX_FIELD_NUMBER: _ClassVar[int]
    SELECTED_BY_REGISTRY_FIELD_NUMBER: _ClassVar[int]
    LOADED_FIELD_NUMBER: _ClassVar[int]
    uuid: str
    format: str
    command: str
    purpose: str
    enabled: bool
    replaces: str
    lastmodified: str
    source_index: int
    selected_by_registry: bool
    loaded: bool
    def __init__(self, uuid: _Optional[str] = ..., format: _Optional[str] = ..., command: _Optional[str] = ..., purpose: _Optional[str] = ..., enabled: bool = ..., replaces: _Optional[str] = ..., lastmodified: _Optional[str] = ..., source_index: _Optional[int] = ..., selected_by_registry: bool = ..., loaded: bool = ...) -> None: ...

class Diagnostic(_message.Message):
    __slots__ = ("record_id", "message")
    RECORD_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    record_id: str
    message: str
    def __init__(self, record_id: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...
