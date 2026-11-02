import argparse
import hashlib
import json
import os
import shutil
import subprocess
import uuid
from types import SimpleNamespace

import pytest

from a3m.client.clientScripts import normalize
from a3m.client.clientScripts.normalize import main
from a3m.client.job import Job
from a3m.main import models
from a3m.main.models import SIP
from a3m.main.models import Derivation
from a3m.main.models import Event
from a3m.main.models import File


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


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="JPEG 2000 normalization requires FFmpeg and FFprobe",
)
@pytest.mark.django_db
def test_normalize_jpeg2000_creates_preservation_tiff(tmp_path, mocker):
    objects = tmp_path / "objects"
    objects.mkdir()
    source = objects / "image with spaces.jp2"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=32x32",
            "-frames:v",
            "1",
            "-c:v",
            "jpeg2000",
            str(source),
        ],
        check=True,
    )
    sip = SIP.objects.create(uuid=str(uuid.uuid4()), currentpath=f"{tmp_path}/")
    location = f"%SIPDirectory%objects/{source.name}"
    original = File.objects.create(
        uuid=str(uuid.uuid4()),
        sip=sip,
        originallocation=location,
        currentlocation=location,
        filegrpuse="original",
    )
    original.fileformatversion_set.create(
        format_version_id="734edb99-968d-42fc-9fc6-342b86fcb6e6",  # x-fmt/392
    )
    task_uuid = str(uuid.uuid4())
    opts = argparse.Namespace(
        purpose="preservation",
        file_uuid=str(original.uuid),
        file_path=str(source),
        sip_path=f"{tmp_path}/",
        sip_uuid=str(sip.uuid),
        task_uuid=task_uuid,
        normalize_file_grp_use="original",
    )

    job = mocker.Mock(spec=Job)
    assert main(job, opts) == 0, job.write_error.call_args_list

    derivative = File.objects.get(uuid=task_uuid, filegrpuse="preservation")
    output = tmp_path / derivative.currentlocation.removeprefix("%SIPDirectory%")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    stream = json.loads(result.stdout)["streams"][0]
    assert (stream["codec_name"], stream["width"], stream["height"]) == ("tiff", 32, 32)
    assert derivative.checksum == hashlib.sha256(output.read_bytes()).hexdigest()
    assert Event.objects.filter(
        file_uuid=original.uuid, event_type="normalization"
    ).exists()
    assert Derivation.objects.filter(
        source_file=original, derived_file=derivative
    ).exists()
