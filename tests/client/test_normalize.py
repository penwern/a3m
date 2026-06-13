import os
import uuid
from types import SimpleNamespace

import pytest

from a3m.client.clientScripts import normalize
from a3m.main import models


class FakeJob:
    def print_output(self, *args):
        pass

    def print_error(self, *args):
        pass


def fake_executor(output_location):
    return SimpleNamespace(
        output_location=str(output_location),
        fpcommand=SimpleNamespace(
            id=str(uuid.uuid4()),
            output_format=SimpleNamespace(
                id=str(uuid.uuid4()),
                format=SimpleNamespace(description="JPEG"),
            ),
        ),
        event_detail_command=None,
        exit_code=0,
    )


def make_opts(purpose, sip_uuid, file_uuid, sip_path):
    return SimpleNamespace(
        purpose=purpose,
        file_uuid=file_uuid,
        task_uuid=str(uuid.uuid4()),
        sip_uuid=sip_uuid,
        sip_path=str(sip_path) + os.sep,
    )


@pytest.fixture
def original_file(db, tmp_path):
    sip_uuid = str(uuid.uuid4())
    file_uuid = str(uuid.uuid4())
    models.SIP.objects.create(uuid=sip_uuid, currentpath=str(tmp_path))
    models.File.objects.create(
        uuid=file_uuid,
        sip_id=sip_uuid,
        originallocation="%transferDirectory%objects/orig.tif",
        currentlocation="%SIPDirectory%objects/orig.tif",
        filegrpuse="original",
    )
    return sip_uuid, file_uuid


@pytest.mark.django_db
def test_once_normalized_does_not_register_thumbnails(tmp_path, original_file):
    """Thumbnails are not part of the package contents, so they must not be
    added to the database (Files, Derivations, format records)."""
    sip_uuid, file_uuid = original_file
    thumbnails_dir = tmp_path / "thumbnails"
    thumbnails_dir.mkdir()
    output = thumbnails_dir / f"{file_uuid}.jpg"
    output.write_bytes(b"not really a jpeg")

    opts = make_opts("thumbnail", sip_uuid, file_uuid, tmp_path)

    normalize.once_normalized(FakeJob(), fake_executor(output), opts, {})

    assert models.File.objects.filter(sip_id=sip_uuid).count() == 1
    assert models.Derivation.objects.count() == 0
    assert models.FileFormatVersion.objects.count() == 0
    assert models.FileID.objects.count() == 0


@pytest.mark.django_db
def test_once_normalized_registers_access_derivatives(tmp_path, original_file):
    sip_uuid, file_uuid = original_file
    dip_objects = tmp_path / "DIP" / "objects"
    dip_objects.mkdir(parents=True)
    output = dip_objects / f"{file_uuid}-orig.jpg"
    output.write_bytes(b"not really a jpeg")

    opts = make_opts("access", sip_uuid, file_uuid, tmp_path)

    normalize.once_normalized(FakeJob(), fake_executor(output), opts, {})

    access_file = models.File.objects.get(uuid=opts.task_uuid)
    assert access_file.filegrpuse == "access"
    assert (
        models.Derivation.objects.filter(
            source_file_id=file_uuid, derived_file_id=opts.task_uuid
        ).count()
        == 1
    )
