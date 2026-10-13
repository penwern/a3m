"""Shared protobuf and JSON representation for preview and live inspection."""

from google.protobuf.json_format import MessageToDict
from google.protobuf.json_format import ParseDict

from a3m.api.fprservice import v1beta1 as api
from a3m.fpr.export import export_registry
from a3m.fpr.registry import Backend


def registry_response(
    backend: Backend, instance_id: str = ""
) -> api.service_pb2.GetRegistryResponse:
    facts = export_registry(backend)
    facts["instance_id"] = instance_id
    return ParseDict(facts, api.service_pb2.GetRegistryResponse())


def registry_json(response: api.service_pb2.GetRegistryResponse) -> dict:
    """Keep snake_case and scalar defaults; absent optional fields stay absent.

    Curate's HTTP adapter must use the equivalent protobuf JSON options.
    """
    return MessageToDict(
        response,
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=True,
    )
