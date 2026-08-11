import pytest

from a3m.client.clientScripts.characterize_file import main
from a3m.client.job import Job
from a3m.main.models import SIP
from a3m.main.models import File
from a3m.main.models import FPCommandOutput

# JPEG (fmt/43): three enabled FPR characterisation rules (FFprobe, ExifTool
# and MediaInfo), all bashScript commands whose text embeds %fileFullName%.
JPEG_FORMAT_VERSION_ID = "05f1242e-127d-4eec-826c-f89571d0283f"


@pytest.fixture
def sip(tmp_path):
    sip_dir = tmp_path / "sip"
    sip_dir.mkdir()
    (sip_dir / "logs").mkdir()

    return SIP.objects.create(currentpath=str(sip_dir))


@pytest.fixture
def jpeg_file(tmp_path, sip):
    d = tmp_path / "dir"
    d.mkdir()
    path = d / "picture.jpg"
    # Content is irrelevant: the tools are mocked; only the identified format
    # version drives FPR rule selection.
    path.write_bytes(b"jpeg-stand-in")

    f = File.objects.create(
        sip=sip, originallocation=str(path), currentlocation=str(path)
    )
    f.fileformatversion_set.create(format_version_id=JPEG_FORMAT_VERSION_ID)

    return f


@pytest.mark.django_db
def test_characterisation_commands_receive_a_real_file_path(mocker, sip, jpeg_file):
    """Placeholders must be substituted before the command is executed.

    The characterisation commands are defined in the FPR registry as
    bashScript text such as ``ffprobe -i "%fileFullName%" ...``. If
    characterize_file passes them through unsubstituted, every tool fails in
    production with errors like ``Error: File not found - %fileFullName%``
    (FFProbe/ExifTool/MediaInfo failure tasks) while the package still
    completes, so nothing surfaces in CI.
    """
    execute_or_run = mocker.patch(
        "a3m.client.clientScripts.characterize_file.executeOrRun",
        return_value=(0, "<mocked-tool-output/>", ""),
    )
    job = mocker.Mock(spec=Job)

    exit_code = main(
        job=job,
        file_path=jpeg_file.currentlocation,
        file_uuid=jpeg_file.uuid,
        sip_uuid=sip.uuid,
    )

    assert exit_code == 0
    # One invocation per enabled JPEG characterisation rule.
    assert execute_or_run.call_count == 3

    for call in execute_or_run.call_args_list:
        script_type, command = call.args[0], call.args[1]
        assert script_type == "bashScript"
        # The whole point of characterisation: the tool gets the actual file.
        assert "%fileFullName%" not in command
        assert str(jpeg_file.currentlocation) in command

    # The successful XML outputs are persisted, one row per rule.
    assert FPCommandOutput.objects.filter(file_id=jpeg_file.uuid).count() == 3
