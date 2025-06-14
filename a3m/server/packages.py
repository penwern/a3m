"""Package management."""

import ast
import collections
import functools
import logging
import os
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from enum import auto
from uuid import uuid4

from django.conf import settings
from google.protobuf import timestamp_pb2

from a3m.api.transferservice import v1beta1 as transfer_service_api
from a3m.archivematicaFunctions import strToUnicode
from a3m.main import models
from a3m.server.db import auto_close_old_connections
from a3m.server.jobs import JobChain
from a3m.server.processing import DEFAULT_PROCESSING_CONFIG
from a3m.server.utils import uuid_from_path

logger = logging.getLogger(__name__)


def _get_setting(name):
    """Retrieve a Django setting decoded as a unicode string."""
    return strToUnicode(getattr(settings, name))


BASE_REPLACEMENTS = {
    r"%tmpDirectory%": os.path.join(_get_setting("SHARED_DIRECTORY"), "tmp", ""),
    r"%processingDirectory%": _get_setting("PROCESSING_DIRECTORY"),
    r"%rejectedDirectory%": _get_setting("REJECTED_DIRECTORY"),
}


def get_file_replacement_mapping(file_obj, unit_directory):
    mapping = BASE_REPLACEMENTS.copy()
    dirname = os.path.dirname(file_obj.currentlocation)
    name, ext = os.path.splitext(file_obj.currentlocation)
    name = os.path.basename(name)

    absolute_path = file_obj.currentlocation.replace(r"%SIPDirectory%", unit_directory)
    absolute_path = absolute_path.replace(r"%transferDirectory%", unit_directory)

    mapping.update(
        {
            r"%fileUUID%": file_obj.pk,
            r"%originalLocation%": file_obj.originallocation,
            r"%currentLocation%": file_obj.currentlocation,
            r"%fileGrpUse%": file_obj.filegrpuse,
            r"%fileDirectory%": dirname,
            r"%fileName%": name,
            r"%fileExtension%": ext[1:],
            r"%fileExtensionWithDot%": ext,
            r"%relativeLocation%": absolute_path,
            # TODO: standardize duplicates
            r"%inputFile%": absolute_path,
            r"%fileFullName%": absolute_path,
        }
    )

    return mapping


class Stage(Enum):
    """Package stages."""

    TRANSFER = auto()
    INGEST = auto()


class Package:
    """Package is the processing unit in a3m.

    It wraps a SIP and borrows its SIP. But it also knows about its transfer
    stage. Some methods return different values depending the stage the
    package is in.
    """

    def __init__(self, name, url, config, transfer, sip):
        self.name = name
        self.url = url
        self.config = self._prepare_config(config)
        self.transfer = transfer
        self.sip = sip
        self.stage = Stage.TRANSFER
        self.aip_filename = None
        self._current_path = self.transfer.currentlocation

    def __repr__(self):
        return "{class_name}({uuid})".format(
            class_name=self.__class__.__name__, uuid=self.uuid
        )

    def _prepare_config(self, provided=None):
        """Combine user-provided processing config with the defaults."""
        config = transfer_service_api.request_response_pb2.ProcessingConfig()
        config.CopyFrom(DEFAULT_PROCESSING_CONFIG)
        if provided is not None:
            for config_field in config.DESCRIPTOR.fields:
                field_name = config_field.name
                setattr(config, field_name, getattr(provided, field_name))

        return config

    @classmethod
    @auto_close_old_connections()
    def create_package(cls, package_queue, executor, workflow, name, url, config):
        """Launch transfer and return its object immediately."""
        if not name:
            raise ValueError("No transfer name provided.")
        if not url:
            raise ValueError("No url provided.")

        transfer_id = str(uuid4())
        transfer_dir = os.path.join(
            _get_setting("PROCESSING_DIRECTORY"), "transfer", transfer_id, ""
        )
        transfer = models.Transfer.objects.create(
            uuid=transfer_id, currentlocation=transfer_dir
        )
        logger.debug("Transfer object created: %s", transfer.pk)

        sip_id = str(uuid4())
        sip_dir = os.path.join(
            _get_setting("PROCESSING_DIRECTORY"), "ingest", sip_id, ""
        )
        sip = models.SIP.objects.create(uuid=sip_id, currentpath=sip_dir)
        sip.transfer_id = transfer_id
        logger.debug("SIP object created: %s", sip.pk)

        package = cls(name, url, config, transfer, sip)

        params = (package, package_queue, workflow)
        future = executor.submit(Package.trigger_workflow, *params)
        future.add_done_callback(
            functools.partial(Package.trigger_workflow_done_callback, package.uuid)
        )

        return package

    @staticmethod
    def trigger_workflow(package, package_queue, workflow):
        logger.debug("Package %s: starting workflow processing", package.uuid)

        initiator_link = workflow.get_initiator()
        if initiator_link is None:
            raise ValueError("Workflow initiator not found")

        job_chain = JobChain(package, workflow, initiator_link)

        package_queue.schedule_job(next(job_chain))

    @staticmethod
    def trigger_workflow_done_callback(package_id, future):
        try:
            future.result()
        except Exception as err:
            logger.warning("Exception detected: %s", err, exc_info=True)
        else:
            logger.info("Package processing started (%s)", package_id)

    @property
    def uuid(self):
        return self.sip.pk

    @property
    def subid(self):
        if self.stage is Stage.INGEST:
            return self.sip.pk
        else:
            return self.transfer.pk

    @property
    def current_path(self):
        return self._current_path

    @current_path.setter
    def current_path(self, value):
        """The real (no shared dir vars) path to the package."""
        self._current_path = value.replace(
            r"%sharedPath%", _get_setting("SHARED_DIRECTORY")
        )

    @property
    def current_path_for_db(self):
        """The path to the package, as stored in the database."""
        return self.current_path.replace(
            _get_setting("SHARED_DIRECTORY"), r"%sharedPath%", 1
        )

    @property
    def context(self):
        """Returns a `PackageContext` for this package."""
        # This needs to be reloaded from the db every time, because new values
        # could have been added by a client script.
        # TODO: pass context changes back from client
        return PackageContext.load_from_db(self.subid)

    @property
    def unit_type(self):
        if self.stage is Stage.INGEST:
            return "unitSIP"
        else:
            return "unitTransfer"

    @property
    def unit_variable_type(self):
        if self.stage is Stage.INGEST:
            return "SIP"
        else:
            return "Transfer"

    @property
    def replacement_path_string(self):
        if self.stage is Stage.INGEST:
            return r"%SIPDirectory%"
        else:
            return r"%transferDirectory%"

    @property  # type: ignore
    @auto_close_old_connections()
    def base_queryset(self):
        if self.stage is Stage.INGEST:
            return models.File.objects.filter(sip_id=self.sip.pk)
        else:
            return models.File.objects.filter(transfer_id=self.transfer.pk)

    def start_ingest(self):
        """Signal this package so it becomes a SIP."""
        self.stage = Stage.INGEST

    @auto_close_old_connections()
    def reload(self):
        if self.stage is Stage.INGEST:
            sip = models.SIP.objects.get(uuid=self.sip.pk)
            self.current_path = sip.currentpath
            self.aip_filename = sip.aip_filename or ""
        else:
            transfer = models.Transfer.objects.get(uuid=self.transfer.pk)
            self.current_path = transfer.currentlocation

    def get_replacement_mapping(self):
        mapping = BASE_REPLACEMENTS.copy()
        mapping.update(
            {
                r"%SIPUUID%": str(self.sip.pk),
                r"%TransferUUID%": str(self.transfer.pk),
                r"%SIPName%": self.name,
                r"%SIPLogsDirectory%": os.path.join(self.current_path, "logs", ""),
                r"%SIPObjectsDirectory%": os.path.join(
                    self.current_path, "objects", ""
                ),
                r"%SIPDirectory%": self.current_path,
                r"%SIPDirectoryBasename%": os.path.basename(
                    os.path.abspath(self.current_path)
                ),
                r"%relativeLocation%": self.current_path_for_db,
            }
        )

        mapping.update(
            {
                rf"%config:{config_attr.name}%": str(
                    getattr(self.config, config_attr.name)
                )
                for config_attr in transfer_service_api.request_response_pb2.ProcessingConfig.DESCRIPTOR.fields
            }
        )

        if self.stage is Stage.INGEST:
            mapping.update(
                {
                    r"%unitType%": self.unit_variable_type,
                    r"%AIPFilename%": self.aip_filename,
                }
            )
        else:
            mapping.update(
                {
                    self.replacement_path_string: self.current_path,
                    r"%unitType%": self.unit_variable_type,
                    r"%URL%": self.url,
                }
            )

        return mapping

    def files(self, filter_subdir=None):
        """Generator that yields all files associated with the package or that
        should be associated with a package.
        """
        with auto_close_old_connections():
            queryset = self.base_queryset

            if filter_subdir:
                filter_path = "".join([self.replacement_path_string, filter_subdir])
                queryset = queryset.filter(currentlocation__startswith=filter_path)

            start_path = self.current_path
            if filter_subdir:
                start_path = start_path + filter_subdir

            files_returned_already = set()
            if queryset.exists():
                for file_obj in queryset.iterator():
                    file_obj_mapped = get_file_replacement_mapping(
                        file_obj, self.current_path
                    )
                    if not os.path.exists(file_obj_mapped.get("%inputFile%")):
                        continue
                    files_returned_already.add(file_obj_mapped.get("%inputFile%"))
                    yield file_obj_mapped

            for basedir, subdirs, files in os.walk(start_path):
                for file_name in files:
                    file_path = os.path.join(basedir, file_name)
                    if file_path not in files_returned_already:
                        yield {
                            r"%relativeLocation%": file_path,
                            r"%fileUUID%": "None",
                            r"%fileGrpUse%": "",
                        }

    @auto_close_old_connections()
    def set_variable(self, key, value, chain_link_id):
        """Sets a UnitVariable, which tracks choices made by users during processing."""
        # TODO: refactor this concept
        if not value:
            value = ""
        else:
            value = str(value)

        unit_var, created = models.UnitVariable.objects.update_or_create(
            unittype=self.unit_variable_type,
            unituuid=self.uuid,
            variable=key,
            defaults=dict(variablevalue=value, microservicechainlink=chain_link_id),
        )
        if created:
            message = "New UnitVariable %s created for %s: %s (MSCL: %s)"
        else:
            message = "Existing UnitVariable %s for %s updated to %s (MSCL" " %s)"

        logger.info(message, key, self.uuid, value, chain_link_id)


class SIPDIP(Package):
    """SIPDIP captures behavior shared between SIP- and DIP-type packages that
    share the same model in Archivematica.
    """

    @classmethod
    @auto_close_old_connections()
    def get_or_create_from_db_by_path(cls, path):
        """Matches a directory to a database SIP by its appended UUID, or path."""
        path = path.replace(_get_setting("SHARED_DIRECTORY"), r"%sharedPath%", 1)
        package_type = cls.unit_variable_type
        sip_uuid = uuid_from_path(path)
        created = True
        if sip_uuid:
            sip_obj, created = models.SIP.objects.get_or_create(
                uuid=sip_uuid,
                defaults={
                    "sip_type": package_type,
                    "currentpath": path,
                    "diruuids": False,
                },
            )
            # Handle the case where transfer_id is None
            if sip_obj.transfer_id is None:
                # Create a Transfer with the same UUID
                transfer, _ = models.Transfer.objects.get_or_create(
                    uuid=sip_uuid, defaults={"currentlocation": path}
                )
            else:
                transfer = models.Transfer.objects.get(pk=sip_obj.transfer_id)
            # TODO: we thought this path was unused but some tests have proved
            # us wrong (see issue #1141) - needs to be investigated.
            if package_type == "SIP" and (not created and sip_obj.currentpath != path):
                sip_obj.currentpath = path
                sip_obj.save()
        else:
            try:
                sip_obj = models.SIP.objects.get(currentpath=path)
                transfer = models.Transfer.objects.get(pk=sip_obj.transfer_id)
                created = False
            except models.SIP.DoesNotExist:
                sip_id = str(uuid4())
                sip_obj = models.SIP.objects.create(
                    uuid=sip_id,
                    currentpath=path,
                    sip_type=package_type,
                    diruuids=False,
                )
                transfer = models.Transfer.objects.create(
                    uuid=sip_id, currentlocation=path
                )
        logger.info(
            "%s %s %s (%s)",
            package_type,
            sip_obj.uuid,
            "created" if created else "updated",
            path,
        )
        return cls(path, sip_obj.uuid, None, transfer, sip_obj)


class DIP(SIPDIP):
    REPLACEMENT_PATH_STRING = r"%SIPDirectory%"
    UNIT_VARIABLE_TYPE = "DIP"
    JOB_UNIT_TYPE = "unitDIP"

    def reload(self):
        # reload is a no-op for DIPs
        pass

    def get_replacement_mapping(self, filter_subdir_path=None):
        mapping = super().get_replacement_mapping()
        mapping[r"%unitType%"] = "DIP"

        if filter_subdir_path:
            relative_location = filter_subdir_path.replace(
                _get_setting("SHARED_DIRECTORY"), r"%sharedPath%", 1
            )
            mapping[r"%relativeLocation%"] = relative_location

        return mapping


class Transfer(Package):
    REPLACEMENT_PATH_STRING = r"%transferDirectory%"
    UNIT_VARIABLE_TYPE = "Transfer"
    JOB_UNIT_TYPE = "unitTransfer"

    def __init__(self, current_path, uuid, url):
        transfer = models.Transfer.objects.get(uuid=uuid)
        if not transfer:
            raise ValueError(f"Transfer with UUID {uuid} not found.")
        # Try to get the corresponding SIP, or create one if it doesn't exist
        try:
            sip = models.SIP.objects.get(pk=transfer.pk)
        except models.SIP.DoesNotExist:
            # Create a SIP with the same UUID as the Transfer
            sip = models.SIP.objects.create(
                uuid=transfer.pk,
                currentpath=transfer.currentlocation,
                sip_type="SIP",
                diruuids=False,
            )
        super().__init__(current_path, uuid, None, transfer, sip)
        self.url = url or ""

    @classmethod
    @auto_close_old_connections()
    def get_or_create_from_db_by_path(cls, path):
        """Matches a directory to a database Transfer by its appended UUID, or path."""
        path = path.replace(_get_setting("SHARED_DIRECTORY"), r"%sharedPath%", 1)

        transfer_uuid = uuid_from_path(path)
        created = True
        if transfer_uuid:
            transfer_obj, created = models.Transfer.objects.get_or_create(
                uuid=transfer_uuid, defaults={"currentlocation": path}
            )
            # TODO: we thought this path was unused but some tests have proved
            # us wrong (see issue #1141) - needs to be investigated.
            if not created and transfer_obj.currentlocation != path:
                transfer_obj.currentlocation = path
                transfer_obj.save()
        else:
            try:
                transfer_obj = models.Transfer.objects.get(currentlocation=path)
                created = False
            except models.Transfer.DoesNotExist:
                transfer_obj = models.Transfer.objects.create(
                    uuid=uuid4(), currentlocation=path
                )
        logger.info(
            "Transfer %s %s (%s)",
            transfer_obj.uuid,
            "created" if created else "updated",
            path,
        )

        return cls(path, transfer_obj.uuid, None)

    @property
    @auto_close_old_connections()
    def base_queryset(self):
        return models.File.objects.filter(transfer_id=self.uuid)

    @auto_close_old_connections()
    def reload(self):
        transfer = models.Transfer.objects.get(uuid=self.uuid)
        self.current_path = transfer.currentlocation
        # self.processing_configuration = transfer.processing_configuration

    def get_replacement_mapping(self):
        mapping = super().get_replacement_mapping()

        mapping.update(
            {
                self.REPLACEMENT_PATH_STRING: self.current_path,
                r"%unitType%": "Transfer",
                # r"%processingConfiguration%": self.processing_configuration,
                r"%URL%": self.url,
            }
        )

        return mapping


class SIP(SIPDIP):
    REPLACEMENT_PATH_STRING = r"%SIPDirectory%"
    UNIT_VARIABLE_TYPE = "SIP"
    JOB_UNIT_TYPE = "unitSIP"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.aip_filename = None
        self.sip_type = None

    @auto_close_old_connections()
    def reload(self):
        sip = models.SIP.objects.get(uuid=self.uuid)
        self.current_path = sip.currentpath
        self.aip_filename = sip.aip_filename or ""

    def get_replacement_mapping(
        self,
    ):
        mapping = super().get_replacement_mapping()

        mapping.update(
            {
                r"%unitType%": "SIP",
                r"%AIPFilename%": self.aip_filename,
                r"%SIPType%": self.sip_type,
            }
        )

        return mapping


class PackageContext:
    """Package context tracks choices made previously while processing"""

    def __init__(self, *items):
        self._data = collections.OrderedDict()
        for key, value in items:
            self._data[key] = value

    def __repr__(self):
        return f"PackageContext({dict(list(self._data.items()))!r})"

    def __iter__(self):
        yield from self._data.items()

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    @classmethod
    @auto_close_old_connections()
    def load_from_db(cls, uuid):
        """
        Loads a context from the UnitVariable table.
        """
        context = cls()

        # TODO: we shouldn't need one UnitVariable per chain, with all the same values
        unit_vars_queryset = models.UnitVariable.objects.filter(
            unituuid=uuid, variable="replacementDict"
        )
        # Distinct helps here, at least
        unit_vars_queryset = unit_vars_queryset.values_list("variablevalue").distinct()
        for unit_var_value in unit_vars_queryset:
            # TODO: nope nope nope, fix eval usage
            try:
                unit_var = ast.literal_eval(unit_var_value[0])
            except (ValueError, SyntaxError):
                logger.exception(
                    "Failed to eval unit variable value %s", unit_var_value[0]
                )
            else:
                context.update(unit_var)

        return context

    def copy(self):
        clone = PackageContext()
        clone._data = self._data.copy()

        return clone

    def update(self, mapping):
        for key, value in mapping.items():
            self._data[key] = value


class PackageNotFoundError(Exception):
    pass


@dataclass
class PackageStatus:
    status: int | None = None
    job: str | None = None
    jobs: list = field(default_factory=list)


@auto_close_old_connections()
def get_package_status(package_queue, package_id: str) -> PackageStatus:
    try:
        sip = models.SIP.objects.get(pk=package_id)
    except models.SIP.DoesNotExist:
        raise PackageNotFoundError

    def get_latest_job(unit_id):
        return (
            models.Job.objects.filter(sipuuid=unit_id)
            .order_by("-createdtime", "-createdtimedec")
            .first()
        )

    package = package_queue.active_packages.get(package_id)
    if package:
        # Reminder: package.subid can be in Transfer or Ingest.
        job = get_latest_job(package.subid)
        return PackageStatus(
            status=transfer_service_api.request_response_pb2.PACKAGE_STATUS_PROCESSING,
            job=job.jobtype if job else None,
        )

    # A3M-TODO: persist package-workflow status!
    # It'd be much easier if a workflow instance could keep the package
    # model(s) up to date.

    # We have an inactive package, look up the status in the database.
    job = get_latest_job(package_id)

    # It must be an error during Transfer when Ingest activity not recorded.
    if not job:
        transfer_id = sip.transfer_id
        if transfer_id is None:
            raise Exception(
                "Package status cannot be determined: transfer_id is undefined"
            )
        job = get_latest_job(sip.transfer_id)
        if job is None:
            return PackageStatus(
                status=transfer_service_api.request_response_pb2.PACKAGE_STATUS_PROCESSING
            )

    if "failed" in job.microservicegroup.lower():
        status = transfer_service_api.request_response_pb2.PACKAGE_STATUS_FAILED
    elif "reject" in job.microservicegroup.lower():
        status = transfer_service_api.request_response_pb2.PACKAGE_STATUS_REJECTED
    elif job.jobtype == "a3m - Store AIP":
        status = transfer_service_api.request_response_pb2.PACKAGE_STATUS_COMPLETE
    else:
        raise Exception(
            f"Package status cannot be determined (job.currentstep={job.currentstep}, job.type={job.jobtype}, job.microservicegroup={job.microservicegroup})"
        )

    package_status = PackageStatus(status=status, job=job.microservicegroup)

    for item in (
        models.Job.objects.filter(sipuuid__in=(sip.pk, sip.transfer_id))
        .order_by("createdtime")
        .values(
            "jobuuid",
            "jobtype",
            "currentstep",
            "microservicegroup",
            "microservicechainlink",
            "currentstep",
            "createdtime",
        )
    ):
        start_time = timestamp_pb2.Timestamp()
        start_time.FromDatetime(item["createdtime"])

        package_status.jobs.append(
            transfer_service_api.request_response_pb2.Job(
                id=str(item["jobuuid"]),
                name=item["jobtype"],
                group=item["microservicegroup"],
                link_id=str(item["microservicechainlink"]),
                status=item["currentstep"],
                start_time=start_time,
            )
        )

    return package_status
