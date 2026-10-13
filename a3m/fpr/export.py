"""Read-only registry facts. These are not predictions of workflow execution."""

import uuid
from copy import deepcopy

from a3m import __version__
from a3m.fpr.registry import Backend
from a3m.fpr.registry import JSONBackend

SCHEMA_VERSION = 1

# Explicit field coverage: changes to the source schema require a deliberate choice.
FIELDS = {
    "formatgroup": ("uuid", "slug", "description"),
    "format": ("uuid", "slug", "description", "group"),
    "formatversion": (
        "uuid",
        "slug",
        "description",
        "format",
        "version",
        "pronom_id",
        "enabled",
        "replaces",
        "lastmodified",
        "access_format",
        "preservation_format",
    ),
    "fptool": ("uuid", "slug", "description", "version", "enabled"),
    "fpcommand": (
        "uuid",
        "description",
        "tool",
        "enabled",
        "replaces",
        "lastmodified",
        "command",
        "command_usage",
        "script_type",
        "output_location",
        "output_format",
        "verification_command",
        "event_detail_command",
    ),
    "fprule": (
        "uuid",
        "format",
        "command",
        "purpose",
        "enabled",
        "replaces",
        "lastmodified",
    ),
}
IGNORED_FIELDS = {"fprule": {"count_attempts", "count_okay", "count_not_okay"}}
COLLECTIONS = {
    "formatgroup": "groups",
    "format": "formats",
    "formatversion": "versions",
    "fptool": "tools",
    "fpcommand": "commands",
    "fprule": "rules",
}


def export_registry(backend: Backend) -> dict:
    """Export source records in loader order, annotated with backend lookup facts.

    Source flags on tools/commands are metadata, not eligibility checks. Registry
    selection does not describe caller fallbacks, retries or processing settings.
    A JSON backend is required because Backend has no enumeration contract yet.
    """
    if not isinstance(backend, JSONBackend):
        raise TypeError("Registry inspection requires a JSONBackend")
    result = {
        "schema_version": SCHEMA_VERSION,
        "source_sha256": backend.source_sha256,
        "a3m_version": __version__,
        **{name: [] for name in COLLECTIONS.values()},
        "diagnostics": [],
    }
    pairs = dict.fromkeys(
        (rule.format.id, rule.purpose) for rule in backend.rules.values()
    )
    selected = {
        str(rule.id)
        for version_id, purpose in pairs
        for rule in backend.get_rules(version_id, purpose)
    }
    for index, item in enumerate(backend.source_records):
        model = item["model"].removeprefix("fpr.")
        fields = item["fields"]
        record = {key: deepcopy(fields[key]) for key in FIELDS[model]}
        record["source_index"] = index
        if model == "formatversion":
            # Lookups use the loaded backend, preserving its first-wins semantics.
            version = backend.get_format_version_by_id(uuid.UUID(fields["uuid"]))
            resolved = (
                backend.get_format_version_by_puid(fields["pronom_id"])
                if fields["pronom_id"]
                else None
            )
            record["active"] = version is not None
            record["resolves_pronom_id"] = (
                resolved is not None and str(resolved.id) == fields["uuid"]
            )
        elif model == "fprule":
            record["selected_by_registry"] = fields["uuid"] in selected
            record["loaded"] = fields["uuid"] not in backend.dropped_rule_ids
            if not record["loaded"]:
                result["diagnostics"].append(
                    {
                        "record_id": fields["uuid"],
                        "message": "Rule was not loaded: missing format or command reference",
                    }
                )
        result[COLLECTIONS[model]].append(record)
    return result
