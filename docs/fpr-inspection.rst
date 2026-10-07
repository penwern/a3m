Read-only FPR inspection
========================

``a3m.api.fprservice.v1beta1.FPRService/GetRegistry`` returns the registry
loaded by the responding server process, on the existing gRPC listener.
It does not reread the JSON per request. The service builds its export on the
first request and caches it. Failures return gRPC ``UNAVAILABLE`` without
preventing the transfer service from starting. A failed request may be retried.

Response contract
-----------------

* ``schema_version``: inspection contract version, currently 1.
* ``source_sha256``: SHA-256 of the exact JSON bytes read by the backend.
* ``a3m_version``: installed package version, separate from source identity.
* ``instance_id``: generated identity for this service instance, distinguishing
  replicas and restarts.
* Ordered arrays of groups, formats, versions, tools, commands and rules.
* Diagnostics for rules dropped due to missing format or command references.

``source_index`` is the zero-based position in the original JSON. Array order
matters for lookups and must be preserved. Optional references distinguish
absence from an empty string. Source references and flags are retained even
where the execution loader does not use them. Stale execution counters
are omitted.

Selection facts and limits
--------------------------

Version ``active`` reflects ``get_format_version_by_id``. ``resolves_pronom_id``
identifies the winner of a non-empty PUID lookup, including duplicate PUIDs.
Rule ``selected_by_registry`` reports whether ``get_rules`` returns it for its
format and purpose. These facts use the existing backend methods.

They do not predict workflow execution: processing settings, caller fallbacks,
retries and command outcomes also matter. Present ``default_*`` rules
as defaults rather than as rules restricted to their placeholder input format.

Tool and command ``enabled`` flags are source metadata: ``get_rules`` does
not enforce them. Tool versions are declared, not detected from installed
binaries.
Historical records remain visible alongside selection annotations. A disabled
replacement still hides its predecessor: neither is selected. The viewer should
make that replacement relationship explicit.

Access and deployment
---------------------

The response contains command bodies. This service shares the existing internal,
unencrypted and unauthenticated gRPC listener; keep it private. Curate's
API must authenticate browser requests and decide which details to expose.
No additional HTTP listener is introduced.

Deploy A3M first. Older engines return gRPC ``UNIMPLEMENTED``, which Curate
should translate into an unavailable state. Use request deadlines. The response
describes one instance, not a guarantee of consistency across all replicas.

Preview and tests
-----------------

With A3M installed, generate preview JSON without starting the server::

    python -m a3m.fpr --output fpr-preview.json
    python -m a3m.fpr --source path/to/initial-data.json --output fpr-preview.json

The CLI preserves array order and sorts object keys. Its instance ID is empty.
It uses the same protobuf JSON conversion as the live API: snake_case names,
explicit scalar defaults and absent optional fields omitted. The Curate HTTP
adapter must use equivalent options; default protobuf JSON options differ.
The JSON backend is required because the abstract backend has no enumeration
contract. A future backend needs an explicit inspection contract.

Focused tests need Django, pytest, grpcio and the generated protobuf runtime,
but no Cells instance, database or preservation tools::

    pytest tests/test_fpr_export.py

Regenerate clients with the pinned plugins in ``buf.gen.yaml``::

    buf lint
    buf generate

Future editing
--------------

No mutation, reload or profile operations are introduced. Future editing needs
validation, durable revisions, explicit activation and stable rules for running
transfers. Normalisation's default lookup currently depends on ``JSONBackend``;
new storage must address that dependency. Rule execution is unchanged here.
