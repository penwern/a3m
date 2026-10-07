"""FPR inspection on A3M's existing internal gRPC server."""

import logging
import threading
import uuid

import grpc

from a3m.api.fprservice import v1beta1 as fpr_service_api
from a3m.fpr.registry import Backend
from a3m.fpr.serialization import registry_response

logger = logging.getLogger(__name__)


class FPRService(fpr_service_api.service_pb2_grpc.FPRServiceServicer):
    def __init__(self, backend: Backend):
        self._backend = backend
        self._instance_id = str(uuid.uuid4())
        self._lock = threading.Lock()
        self._response = None

    def GetRegistry(self, request, context):
        # Build once on demand. Inspection failures must not prevent transfers
        # from starting, and concurrent first requests must share one snapshot.
        with self._lock:
            if self._response is None:
                try:
                    self._response = registry_response(self._backend, self._instance_id)
                except Exception:
                    logger.exception("Could not build FPR inspection snapshot")
                    context.abort(
                        grpc.StatusCode.UNAVAILABLE, "FPR inspection is unavailable"
                    )
            response = fpr_service_api.service_pb2.GetRegistryResponse()
            response.CopyFrom(self._response)
            return response
