import gzip
from datetime import date

import pytest
from event_logs.collect_game_event_logs_dag import (
    fetch_gzipped,
    select_files,
    verify_gzip,
)

RUN = date(2026, 11, 23)


def test_select_only_finished_dates():
    remote = [
        "2026-11-20.101.jsonl",
        "2026-11-21.101.jsonl",  # run - 2: finished at 11-22 15:00Z
        "2026-11-22.101.jsonl",  # still active
        "2026-11-23.101.jsonl",
    ]
    assert select_files(remote, [], RUN) == [
        "2026-11-20.101.jsonl",
        "2026-11-21.101.jsonl",
    ]


def test_skip_already_fetched_per_pid():
    remote = ["2026-11-20.101.jsonl", "2026-11-20.102.jsonl"]
    local = ["2026-11-20.101.jsonl.gz"]
    assert select_files(remote, local, RUN) == ["2026-11-20.102.jsonl"]


def test_include_loguru_renamed_file():
    remote = ["2026-11-20.101.2026-11-20_15-00-00_000000.jsonl"]
    assert select_files(remote, [], RUN) == remote


def test_ignore_unrelated_names():
    remote = [
        "2026-11-20.jsonl.zip",
        "2026-11-20.jsonl",
        "notes.txt",
        "2026-11-20.101.jsonl.tmp",
    ]
    assert select_files(remote, [], RUN) == []


class FakeChannel:
    def __init__(self, status):
        self.status = status

    def recv_exit_status(self):
        return self.status


class FakeStream:
    def __init__(self, data: bytes, status: int = 0):
        import io

        self._buf = io.BytesIO(data)
        self.channel = FakeChannel(status)

    def read(self, *args):
        return self._buf.read(*args)


class FakeSSH:
    def __init__(self, data: bytes, status: int = 0):
        self.data, self.status = data, status

    def exec_command(self, cmd):
        return None, FakeStream(self.data, self.status), FakeStream(b"err")


def test_fetch_gzipped_writes_verified_file(tmp_path):
    payload = gzip.compress(b'{"a":1}\n{"a":2}\n')
    dest = tmp_path / "x.jsonl.gz"
    assert fetch_gzipped(FakeSSH(payload), "/r/x.jsonl", str(dest)) == 2
    assert verify_gzip(str(dest)) == 2
    assert not (tmp_path / "x.jsonl.gz.tmp").exists()


@pytest.mark.parametrize(
    "payload,status",
    [
        (gzip.compress(b"a\n"), 1),  # remote gzip failed
        (gzip.compress(b"a\nb\n")[:-5], 0),  # truncated stream
    ],
)
def test_fetch_gzipped_leaves_nothing_on_failure(tmp_path, payload, status):
    dest = tmp_path / "x.jsonl.gz"
    with pytest.raises(Exception):
        fetch_gzipped(FakeSSH(payload, status), "/r/x.jsonl", str(dest))
    assert list(tmp_path.iterdir()) == []
