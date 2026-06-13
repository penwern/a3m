import os
import uuid

import pytest

from a3m.client.clientScripts import manual_normalization_move_access_files_to_dip
from a3m.client.job import Job


@pytest.mark.django_db
def test_unmatched_access_file_without_csv_reports_missing_original(tmp_path):
    """When no original matches the access file and there is no
    normalization.csv, the job must fail with exit code 3 and a readable
    message, not crash."""
    sip_uuid = str(uuid.uuid4())
    sip_dir = str(tmp_path) + os.sep
    file_path = os.path.join(
        sip_dir, "objects", "manualNormalization", "access", "foo.txt"
    )

    job = Job(
        "manual_normalization_move_access_files_to_dip",
        str(uuid.uuid4()),
        ["--sipUUID", sip_uuid, "--sipDirectory", sip_dir, "--filePath", file_path],
    )

    manual_normalization_move_access_files_to_dip.call([job])

    assert job.get_exit_code() == 3
    assert "No matching file" in job.get_stderr()
