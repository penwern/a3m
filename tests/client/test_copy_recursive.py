import uuid

from a3m.client.clientScripts import copy_recursive
from a3m.client.job import Job


def test_copy_recursive_processes_remaining_jobs_after_missing_source(tmp_path):
    """A missing source directory means nothing to copy for that job, but the
    remaining jobs in the batch must still run."""
    missing_src = tmp_path / "does-not-exist"
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "sub" / "file.txt").write_text("content")
    dst = tmp_path / "dst"
    dst.mkdir()

    job_missing = Job("copy_recursive", str(uuid.uuid4()), [str(missing_src), str(dst)])
    job_real = Job("copy_recursive", str(uuid.uuid4()), [str(src), str(dst)])

    copy_recursive.call([job_missing, job_real])

    assert (dst / "src" / "sub" / "file.txt").exists()
    assert job_missing.get_exit_code() == 0
    assert job_real.get_exit_code() == 0
