"""Registry inspection tests need neither Cells nor a preservation database."""

import hashlib
import json
import os
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from importlib.resources import files

import grpc
import pytest

from a3m.api.fprservice import v1beta1 as api
from a3m.fpr.export import FIELDS
from a3m.fpr.export import IGNORED_FIELDS
from a3m.fpr.export import export_registry
from a3m.fpr.registry import JSONBackend
from a3m.fpr.registry import RulePurpose
from a3m.fpr.serialization import registry_json
from a3m.fpr.serialization import registry_response
from a3m.server import fpr_service
from a3m.server.fpr_service import FPRService


@pytest.fixture(scope="module")
def blob():
    return files("a3m.fpr.migrations").joinpath("initial-data.json").read_bytes()


@pytest.fixture(scope="module")
def backend(blob):
    return JSONBackend(blob)


def test_source_identity_and_order(blob, backend):
    exported = export_registry(backend)
    assert exported["source_sha256"] == hashlib.sha256(blob).hexdigest()
    assert JSONBackend(blob.decode()).source_sha256 == backend.source_sha256
    assert JSONBackend(blob + b"\n").source_sha256 != backend.source_sha256
    records = sorted(
        (
            record
            for key in ("groups", "formats", "versions", "tools", "commands", "rules")
            for record in exported[key]
        ),
        key=lambda record: record["source_index"],
    )
    assert [record["uuid"] for record in records] == [
        item["fields"]["uuid"] for item in json.loads(blob)
    ]


def test_source_field_audit(backend):
    for item in backend.source_records:
        model = item["model"].removeprefix("fpr.")
        assert set(item["fields"]) == set(FIELDS[model]) | IGNORED_FIELDS.get(
            model, set()
        )


def test_selection_matches_backend(backend):
    exported = export_registry(backend)
    for record in exported["versions"]:
        version_id = uuid.UUID(record["uuid"])
        assert record["active"] == (
            backend.get_format_version_by_id(version_id) is not None
        )
        resolved = (
            backend.get_format_version_by_puid(record["pronom_id"])
            if record["pronom_id"]
            else None
        )
        assert record["resolves_pronom_id"] == (
            resolved is not None and str(resolved.id) == record["uuid"]
        )
        for purpose in RulePurpose:
            actual = [
                rule["uuid"]
                for rule in exported["rules"]
                if rule["format"] == record["uuid"]
                and rule["purpose"] == purpose.value
                and rule["selected_by_registry"]
            ]
            assert actual == [
                str(rule.id) for rule in backend.get_rules(version_id, purpose)
            ]


def test_tiff_golden_fact(backend):
    # Human-checked source fact: TIFF fmt/353 preserves via convert to TIFF.
    exported = export_registry(backend)
    version = next(
        v
        for v in exported["versions"]
        if v["pronom_id"] == "fmt/353" and v["resolves_pronom_id"]
    )
    rule = next(
        r
        for r in exported["rules"]
        if r["format"] == version["uuid"]
        and r["purpose"] == "preservation"
        and r["selected_by_registry"]
    )
    command = next(c for c in exported["commands"] if c["uuid"] == rule["command"])
    tool = next(t for t in exported["tools"] if t["uuid"] == command["tool"])
    output = next(
        v for v in exported["versions"] if v["uuid"] == command["output_format"]
    )
    assert command["description"] == "Transcoding to tif with convert"
    assert tool["description"] == "convert"
    assert output["description"] == "TIFF"


def test_source_flags_do_not_hide_selected_rule(blob):
    data = json.loads(blob)
    rules = [item["fields"] for item in data if item["model"] == "fpr.fprule"]
    replaced = {r["replaces"] for r in rules if r["replaces"]}
    rule = next(r for r in rules if r["enabled"] and r["uuid"] not in replaced)
    command = next(
        i["fields"]
        for i in data
        if i["model"] == "fpr.fpcommand" and i["fields"]["uuid"] == rule["command"]
    )
    tool = next(
        i["fields"]
        for i in data
        if i["model"] == "fpr.fptool" and i["fields"]["uuid"] == command["tool"]
    )
    command["enabled"] = False
    tool["enabled"] = False
    result = export_registry(JSONBackend(json.dumps(data)))
    assert next(r for r in result["rules"] if r["uuid"] == rule["uuid"])[
        "selected_by_registry"
    ]
    assert not next(t for t in result["tools"] if t["uuid"] == tool["uuid"])["enabled"]


def test_replacement_and_dropped_rule_diagnostics(blob):
    data = json.loads(blob)
    original = next(
        i for i in data if i["model"] == "fpr.fprule" and i["fields"]["enabled"]
    )
    replacement = deepcopy(original)
    replacement["fields"].update(
        uuid=str(uuid.uuid4()), replaces=original["fields"]["uuid"], enabled=False
    )
    dangling = deepcopy(original)
    dangling["fields"].update(uuid=str(uuid.uuid4()), command=str(uuid.uuid4()))
    data.extend([replacement, dangling])
    result = export_registry(JSONBackend(json.dumps(data)))
    by_id = {r["uuid"]: r for r in result["rules"]}
    assert not by_id[original["fields"]["uuid"]]["selected_by_registry"]
    assert not by_id[replacement["fields"]["uuid"]]["selected_by_registry"]
    assert not by_id[dangling["fields"]["uuid"]]["loaded"]
    assert result["diagnostics"][0]["record_id"] == dangling["fields"]["uuid"]


def test_duplicate_puid_uses_version_order(blob):
    data = json.loads(blob)
    versions = [i for i in data if i["model"] == "fpr.formatversion"]
    replaced = {i["fields"]["replaces"] for i in versions if i["fields"]["replaces"]}
    first, second = [
        i
        for i in versions
        if i["fields"]["enabled"] and i["fields"]["uuid"] not in replaced
    ][:2]
    for item in (first, second):
        item["fields"]["pronom_id"] = "test/duplicate"
    result = export_registry(JSONBackend(json.dumps(data)))
    matches = [v for v in result["versions"] if v["pronom_id"] == "test/duplicate"]
    assert [v["resolves_pronom_id"] for v in matches] == [True, False]
    data.reverse()
    matches = [
        v
        for v in export_registry(JSONBackend(json.dumps(data)))["versions"]
        if v["pronom_id"] == "test/duplicate"
    ]
    assert matches[0]["uuid"] == second["fields"]["uuid"]
    assert [v["resolves_pronom_id"] for v in matches] == [True, False]


def test_cli_determinism_across_hash_seeds(tmp_path, backend):
    outputs = []
    for seed in ("1", "17"):
        target = tmp_path / f"registry-{seed}.json"
        subprocess.run(
            [sys.executable, "-m", "a3m.fpr", "--output", str(target)],
            env={**os.environ, "PYTHONHASHSEED": seed},
            check=True,
        )
        outputs.append(target.read_bytes())
    assert outputs[0] == outputs[1]
    live = registry_json(FPRService(backend).GetRegistry(None, None))
    live["instance_id"] = ""
    preview = json.loads(outputs[0])
    assert preview == live
    assert preview["groups"][0]["source_index"] == 0 or any(
        r["source_index"] == 0 for r in preview["formats"]
    )
    assert any(v["active"] is False for v in preview["versions"])


def test_grpc_roundtrip_and_snapshot(backend):
    service = FPRService(backend)
    expected = service.GetRegistry(None, None)
    assert expected.ByteSize() < 4 * 1024 * 1024
    assert expected.instance_id
    absent = next(v for v in expected.versions if not v.HasField("replaces"))
    assert not absent.HasField("replaces")
    with ThreadPoolExecutor(max_workers=1) as executor:
        server = grpc.server(executor)
        api.service_pb2_grpc.add_FPRServiceServicer_to_server(service, server)
        port = server.add_insecure_port("127.0.0.1:0")
        server.start()
        try:
            with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
                response = api.service_pb2_grpc.FPRServiceStub(channel).GetRegistry(
                    api.service_pb2.GetRegistryRequest(), timeout=10
                )
                assert response == expected
                del response.rules[:]
                assert service.GetRegistry(None, None) == expected
        finally:
            server.stop(0).wait()


@pytest.mark.parametrize("value", [None, ""])
def test_nullable_scalar_presence(blob, value):
    data = json.loads(blob)
    version = next(i["fields"] for i in data if i["model"] == "fpr.formatversion")
    command = next(i["fields"] for i in data if i["model"] == "fpr.fpcommand")
    version["version"] = value
    command["output_location"] = value
    response = registry_response(JSONBackend(json.dumps(data)))
    assert response.versions[0].HasField("version") == (value is not None)
    assert response.commands[0].HasField("output_location") == (value is not None)
    payload = registry_json(response)
    for record, key in [
        (payload["versions"][0], "version"),
        (payload["commands"][0], "output_location"),
    ]:
        assert (key in record) == (value is not None)
        if value is not None:
            assert record[key] == value


def test_lazy_concurrent_snapshot_build(backend, monkeypatch):
    calls = []
    barrier = threading.Barrier(8)

    def build(source, instance_id):
        calls.append(source)
        return api.service_pb2.GetRegistryResponse(
            schema_version=1,
            instance_id=instance_id,
        )

    monkeypatch.setattr(fpr_service, "registry_response", build)
    service = FPRService(backend)
    assert calls == []  # Construction must not inspect the registry.

    def request(_):
        barrier.wait(timeout=10)
        return service.GetRegistry(None, None)

    with ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(executor.map(request, range(8)))
    assert calls == [backend]
    assert all(r == responses[0] for r in responses)
    responses[0].schema_version = 999
    assert service.GetRegistry(None, None).schema_version == 1


@pytest.mark.parametrize("failure", [TypeError, ValueError])
def test_inspection_failure_is_unavailable_and_retryable(backend, monkeypatch, failure):
    calls = []

    def fail(source, instance_id):
        calls.append(source)
        raise failure("private diagnostic details")

    monkeypatch.setattr(fpr_service, "registry_response", fail)
    service = FPRService(backend)
    assert calls == []
    with ThreadPoolExecutor(max_workers=1) as executor:
        server = grpc.server(executor)
        api.service_pb2_grpc.add_FPRServiceServicer_to_server(service, server)
        port = server.add_insecure_port("127.0.0.1:0")
        server.start()
        try:
            with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
                stub = api.service_pb2_grpc.FPRServiceStub(channel)
                with pytest.raises(grpc.RpcError) as error:
                    stub.GetRegistry(api.service_pb2.GetRegistryRequest(), timeout=10)
                assert error.value.code() == grpc.StatusCode.UNAVAILABLE
                assert "private" not in error.value.details()
                monkeypatch.setattr(fpr_service, "registry_response", registry_response)
                response = stub.GetRegistry(
                    api.service_pb2.GetRegistryRequest(), timeout=10
                )
                assert response.source_sha256 == backend.source_sha256
        finally:
            server.stop(0).wait()


def test_only_existing_pairs_are_looked_up(backend, monkeypatch):
    calls = []
    lookup = backend.get_rules

    def track(version_id, purpose):
        calls.append((version_id, purpose))
        return lookup(version_id, purpose)

    monkeypatch.setattr(backend, "get_rules", track)
    export_registry(backend)
    expected = {(r.format.id, r.purpose) for r in backend.rules.values()}
    assert set(calls) == expected
    assert len(calls) == len(expected)
