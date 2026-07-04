"""End-to-end characterisation coverage.

Submits a real transfer through the embedded gRPC server with one file per
media family and asserts that every characterisation, validation and
normalization tool invocation succeeded:

- FFprobe / ExifTool / MediaInfo (characterize_file) on jpg/png/mp3/wav/mp4
- JHOVE (validate_file) on jpg/tif/wav
- FFmpeg (normalize) on the audio/video files

The package-level status cannot catch these failures: the characterise job's
fallback link continues the workflow, so a package whose every tool failed
still reports COMPLETE. The assertions therefore inspect per-task results.

Requires the real tools on PATH (the Docker image has them all); skipped
otherwise. To run locally without installing the tools, use the image's
tools-only base stage with the repo venv mounted in:

    docker build --target base -t a3m-base:test .
    docker run --rm --user 1000:1000 -e HOME=/tmp/a3mhome \
        -e PATH="$PWD/.venv/bin:/usr/local/bin:/usr/bin:/bin" \
        -v "$HOME:$HOME" -w "$PWD" a3m-base:test \
        bash -c "mkdir -p /tmp/a3mhome && pytest tests/server/test_characterization_e2e.py"

The venv bin must be on PATH: the JHOVE FPR command is a python script whose
subprocess resolution needs a bare `python` (the production image provides it
via /app/.venv/bin).
"""

import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from a3m.api.transferservice.v1beta1.request_response_pb2 import PACKAGE_STATUS_COMPLETE
from a3m.api.transferservice.v1beta1.request_response_pb2 import ProcessingConfig
from a3m.cli.client.wrapper import ClientWrapper
from a3m.fpr.registry import FPR
from a3m.main import models

REQUIRED_TOOLS = ("ffprobe", "ffmpeg", "exiftool", "mediainfo", "jhove", "convert")
MISSING_TOOLS = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        bool(MISSING_TOOLS), reason=f"tools not installed: {MISSING_TOOLS}"
    ),
]

# No thumbnails, transcription or policy checks: they pull in further tools
# (tesseract, mediaconch) without adding characterisation coverage.
PROCESSING_CONFIG = ProcessingConfig(
    assign_uuids_to_directories=True,
    extract_packages=True,
    identify_transfer=True,
    identify_submission_and_metadata=True,
    identify_before_normalization=True,
    normalize=True,
    transcribe_files=False,
    perform_policy_checks_on_originals=False,
    perform_policy_checks_on_preservation_derivatives=False,
    perform_policy_checks_on_access_derivatives=False,
    aip_compression_level=1,
    aip_compression_algorithm=ProcessingConfig.AIP_COMPRESSION_ALGORITHM_S7_COPY,
    thumbnail_mode=ProcessingConfig.THUMBNAIL_MODE_DO_NOT_GENERATE,
    generate_dip=False,
)


def _write_wav(path: Path):
    """One second of PCM16 mono silence (fmt/141, JHOVE-validatable)."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 8000)


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", *args], check=True)


@pytest.fixture
def transfer_dir(tmp_path):
    """One generated file per media family.

    The media fixtures committed to the repo (evelyn_s_photo.jpg etc.) are
    0-byte placeholders, so everything is synthesised here with the same
    tools the test requires anyway.
    """
    src = tmp_path / "transfer-source"
    src.mkdir()

    video = "testsrc=duration=1:size=64x64:rate=5"
    _ffmpeg("-f", "lavfi", "-i", video, "-frames:v", "1", str(src / "sample.jpg"))
    _ffmpeg("-f", "lavfi", "-i", video, "-frames:v", "1", str(src / "sample.png"))
    _ffmpeg("-f", "lavfi", "-i", video, "-pix_fmt", "yuv420p", str(src / "sample.mp4"))
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=1",
        "-codec:a",
        "libmp3lame",
        str(src / "sample.mp3"),
    )
    subprocess.run(
        ["convert", "-size", "64x64", "xc:white", str(src / "sample.tif")], check=True
    )
    _write_wav(src / "sample.wav")

    return src


@pytest.fixture
def shared_dirs(tmp_path, settings, mocker):
    settings.SHARED_DIRECTORY = str(tmp_path / "shared") + "/"
    settings.PROCESSING_DIRECTORY = str(tmp_path / "shared" / "processing") + "/"
    settings.REJECTED_DIRECTORY = str(tmp_path / "shared" / "rejected") + "/"
    # BASE_REPLACEMENTS is computed from settings at import time.
    mocker.patch.dict(
        "a3m.server.packages.BASE_REPLACEMENTS",
        {
            r"%tmpDirectory%": str(tmp_path / "shared" / "tmp") + "/",
            r"%processingDirectory%": settings.PROCESSING_DIRECTORY,
            r"%rejectedDirectory%": settings.REJECTED_DIRECTORY,
        },
    )


@pytest.fixture
def fresh_task_backend():
    """The embedded server shuts down the process-global task backend's
    executor on exit (runner.py), and get_task_backend() keeps returning the
    dead singleton, so any later test that submits tasks fails with "cannot
    schedule new futures after shutdown". Isolate this test's backend and
    leave a clean slate behind.
    """
    # Deferred import: a3m.server.tasks circularly imports a3m.server.jobs, so
    # importing it at module level breaks collection when this file is the
    # first to touch the package (e.g. a single-file pytest invocation).
    from a3m.server.tasks import backends

    backends.backend_global = None
    yield
    backends.backend_global = None


def _tool_for_rule(rule_id):
    rule = FPR.get_rule_by_id(str(rule_id))
    return rule.command.description if rule else f"unknown rule {rule_id}"


def _task_failures(execution, ok_exit_codes=(0,)):
    """Failure descriptions for one client script, empty when all succeeded."""
    tasks = list(models.Task.objects.filter(execution=execution))
    if not tasks:
        return [f"[{execution}] no tasks ran at all"]
    failures = [
        f"[{execution}] {t.filename}: exit {t.exitcode}\n"
        f"    stdout: {(t.stdout or '').strip()[:300]}\n"
        f"    stderr: {(t.stderror or '').strip()[:300]}"
        for t in tasks
        if t.exitcode not in ok_exit_codes
    ]
    failures.extend(
        f"[{execution}] {t.filename}: ran with unsubstituted %fileFullName%"
        for t in tasks
        if t.exitcode == 0
        and (
            "%fileFullName%" in (t.stderror or "")
            or "%fileFullName%" in (t.stdout or "")
        )
    )
    return failures


def test_characterisation_tools_run_successfully(
    transfer_dir, shared_dirs, fresh_task_backend
):
    with ClientWrapper() as cw:
        resp = cw.client.submit(
            url=f"file://{transfer_dir}",
            name="characterisation-e2e",
            config=PROCESSING_CONFIG,
        )
        result = cw.client.wait_until_complete(resp.id)

    # Collect every problem before asserting so one run reports the state of
    # all tools, not just the first broken one.
    failures = []

    failed_jobs = list(
        models.Job.objects.filter(currentstep=models.Job.STATUS_FAILED).values_list(
            "jobtype", "microservicegroup"
        )
    )

    if result.status != PACKAGE_STATUS_COMPLETE:
        # Name every failed job so a failure outside the watched groups (e.g.
        # Compress AIP with no 7z on PATH) is still diagnosable from the report.
        failures.append(
            f"package finished with status {result.status}; "
            f"failed jobs: {failed_jobs}"
        )

    # No characterise/validate/normalize job may end Failed.
    failures.extend(
        f"job failed: {jobtype} (group: {group})"
        for jobtype, group in failed_jobs
        if "characterize" in group.lower()
        or "validat" in group.lower()
        or "normalize" in group.lower()
    )

    # Every tool invocation exited 0 with substituted placeholders.
    failures.extend(_task_failures("characterize_file"))  # FFprobe/ExifTool/MediaInfo
    failures.extend(_task_failures("validate_file"))  # JHOVE
    # normalize exit 2 is NO_RULE_FOUND, a legitimate outcome the workflow
    # maps to success; exit 1 (RULE_FAILED) is a real tool failure.
    failures.extend(_task_failures("normalize", ok_exit_codes=(0, 2)))  # FFmpeg/convert

    # Each characterisation tool actually produced saved XML output.
    tools_with_output = {
        _tool_for_rule(out.rule_id) for out in models.FPCommandOutput.objects.all()
    }
    failures.extend(
        f"{tool} produced no saved characterisation output "
        f"(tools with output: {sorted(tools_with_output)})"
        for tool in ("FFprobe", "ExifTool", "MediaInfo")
        if tool not in tools_with_output
    )

    assert not failures, "\n".join(["characterisation coverage failures:", *failures])
