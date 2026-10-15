import os
import random
import subprocess
import threading
import time

import pytest

from agent_v3.tools import shell
from agent_v3.tools.registry import ErrorCode


def cmd(env, command, **kw):
    return env.call("run_command", command=command, **kw)


def survivors(marker: str) -> list[int]:
    """PIDs of processes whose command line contains `marker` (excluding this probe itself)."""
    if os.name == "nt":
        ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*" + marker +
              "*' -and $_.ProcessId -ne $PID } | ForEach-Object { $_.ProcessId }")
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    else:
        out = subprocess.run(["pgrep", "-f", marker], capture_output=True, text=True).stdout
    return [int(x) for x in out.split()]


def wait_for(predicate, timeout=15.0, interval=0.2):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def run_in_thread(fn):
    box = {}
    t = threading.Thread(target=lambda: box.setdefault("result", fn()), daemon=True)
    t.start()
    return t, box


# --- basics --------------------------------------------------------------------------------------

def test_shell_is_not_wsl():
    assert "system32" not in shell.find_shell().lower()


def test_agent_shell_env_var_wins(monkeypatch):
    shell.find_shell.cache_clear()
    monkeypatch.setenv("AGENT_SHELL", "/custom/bash")
    try:
        assert shell.find_shell() == "/custom/bash"
    finally:
        shell.find_shell.cache_clear()


def test_exit_zero(env):
    r = cmd(env, "echo hello")
    assert r.ok and r.error_code is None
    header, body = r.output.split("\n", 1)
    assert header.startswith("Exit code 0 · ") and header.endswith("s") and body == "hello"
    assert r.metadata["exit_code"] == 0 and r.metadata["duration_s"] >= 0
    assert r.summary.startswith("exit 0 · ")


def test_nonzero_exit_returns_full_output_and_is_not_ok(env):
    r = cmd(env, "echo out; echo err >&2; exit 3")
    assert not r.ok and r.error_code == ErrorCode.NONZERO_EXIT
    assert r.output.startswith("Error (nonzero_exit): Exit code 3 · ")
    assert "out" in r.output and "err" in r.output
    assert r.metadata["exit_code"] == 3 and r.summary.startswith("exit 3")


def test_no_output_is_just_the_header(env):
    assert "\n" not in cmd(env, "true").output


def test_stdin_is_closed(env):
    r = cmd(env, "cat; echo done", timeout=10)
    assert r.ok and r.output.endswith("done")


def test_cwd_defaults_to_workspace_and_can_be_overridden(env):
    env.write("sub/x.txt", "x")
    assert "sub" in cmd(env, "pwd", cwd="sub").output
    assert "ws" in cmd(env, "pwd").output
    assert env.requests[-1].cwd == str(env.root) and not env.requests[-1].outside_workspace


def test_cwd_must_exist(env):
    r = cmd(env, "pwd", cwd="nope")
    assert r.error_code == ErrorCode.NOT_FOUND and env.requests == []


def test_environment_is_tuned_for_low_noise(env):
    r = cmd(env, 'echo "$NO_COLOR $TERM $GIT_PAGER $PAGER $PYTHONUNBUFFERED $PYTHONIOENCODING"')
    assert r.output.endswith("1 dumb cat cat 1 utf-8")


def test_unicode_output(env):
    assert cmd(env, "printf 'caf\\xc3\\xa9 \\xe2\\x9c\\x93'").output.endswith("café ✓")


def test_ansi_escapes_are_stripped(env):
    r = cmd(env, r"printf '\033[31mred\033[0m \033[1;32mgreen\033[0m\n'")
    assert "\x1b" not in r.output and r.output.endswith("red green")


# --- approval ------------------------------------------------------------------------------------

def test_approval_request_describes_the_command(env):
    cmd(env, "echo hi", timeout=7)
    [req] = env.requests
    assert (req.kind, req.title, req.command, req.timeout) == ("command", "Run command", "echo hi", 7)
    assert req.cwd == str(env.root) and req.outside_workspace is False


def test_rejected_command_does_not_run(env):
    env.reject("use pytest -x instead")
    r = cmd(env, "touch ran.txt")
    assert r.error_code == ErrorCode.REJECTED
    assert r.output == "Error (rejected): The user rejected this command.\nUser feedback: use pytest -x instead"
    assert not (env.root / "ran.txt").exists()


def test_cwd_outside_workspace_is_flagged(env, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    cmd(env, "pwd", cwd=str(other))
    assert env.requests[0].outside_workspace is True and env.requests[0].reason == "cwd outside workspace"


def test_timeout_is_clamped_to_config_max(make_env):
    env = make_env(command_max_timeout=5)
    cmd(env, "true", timeout=600)
    assert env.requests[0].timeout == 5


# --- truncation ----------------------------------------------------------------------------------

def test_truncation_saves_full_log_and_keeps_tail(make_env):
    env = make_env(tool_output_max_chars=1000)
    r = cmd(env, "for i in $(seq 1 2000); do echo line $i; done")
    assert r.ok and r.metadata["truncated"] is True
    assert "line 1\n" in r.output and "line 2000" in r.output          # head and tail survive
    assert "line 1000\n" not in r.output
    assert len(r.output) < 1400
    rel = r.metadata["full_output_path"]
    assert rel.startswith(".agent_v3/outputs/c") and rel.endswith(".log")     # named by call_id
    assert f"Full output saved to {rel}" in r.output and "chars total" in r.output
    full = (env.root / rel).read_text(encoding="utf-8")
    assert "line 1000\n" in full and full.count("line ") == 2000
    # The saved log is searchable even though .agent_v3 is an ignored dir.
    hit = env.call("search_text", pattern="line 1000", path=rel)
    assert hit.ok and hit.metadata["matches"] == 1


def test_tail_gets_more_budget_than_head(make_env):
    env = make_env(tool_output_max_chars=1000)
    r = cmd(env, "head -c 3000 /dev/zero | tr '\\0' H; head -c 3000 /dev/zero | tr '\\0' T")
    body = r.output.split("\n", 1)[1]
    assert body.count("H") == 400 and body.count("T") == 600


def test_small_output_is_not_truncated(env):
    r = cmd(env, "echo small")
    assert "truncated" not in r.metadata and not (env.root / ".agent_v3").exists()


# --- timeout / cancel kill the process tree --------------------------------------------------------

def unique_marker() -> str:
    """A sleep duration no other process uses, so survivors() can't see leftovers from other runs."""
    return str(random.randint(100_000, 999_999))


def test_timeout_kills_the_whole_process_tree(env):
    marker = unique_marker()
    t, box = run_in_thread(lambda: cmd(env, f"sleep {marker} & sleep {marker}", timeout=3))
    assert wait_for(lambda: survivors(marker)), "child processes never started"
    t.join(30)
    r = box["result"]
    assert not r.ok and r.error_code == ErrorCode.TIMEOUT
    assert r.output.startswith("Error (timeout): Timed out after 3s (process tree killed)")
    assert r.summary == "timeout · 3s"
    assert wait_for(lambda: not survivors(marker), timeout=10), f"survivors: {survivors(marker)}"


def test_timeout_keeps_output_produced_before_the_kill(env):
    marker = unique_marker()
    r = cmd(env, f"echo started; sleep {marker}", timeout=2)
    assert r.error_code == ErrorCode.TIMEOUT and "started" in r.output
    assert r.metadata["duration_s"] < 4                      # returned promptly, not after a pipe wait
    assert wait_for(lambda: not survivors(marker), timeout=10)


def test_cancel_mid_run_kills_tree_and_returns_quickly(env):
    marker = unique_marker()
    t, box = run_in_thread(lambda: cmd(env, f"echo before; sleep {marker} & sleep {marker}", timeout=60))
    assert wait_for(lambda: survivors(marker)), "child processes never started"
    started = time.monotonic()
    env.cancel.cancel()
    t.join(30)
    assert time.monotonic() - started < 10
    r = box["result"]
    assert not r.ok and r.error_code == ErrorCode.CANCELLED
    assert r.output.startswith("Error (cancelled): Cancelled by user") and "before" in r.output
    assert wait_for(lambda: not survivors(marker), timeout=10), f"survivors: {survivors(marker)}"


def test_cancelled_before_start_does_not_run(env):
    env.cancel.cancel()
    r = cmd(env, "touch ran.txt")
    assert r.error_code == ErrorCode.CANCELLED and not (env.root / "ran.txt").exists()


def test_process_is_unregistered_after_completion(env):
    cmd(env, "true")
    assert env.cancel._procs == set()


# --- git tools -----------------------------------------------------------------------------------

def git(env, *argv):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *argv], cwd=env.root,
                   check=True, capture_output=True)


@pytest.fixture
def repo(env):
    git(env, "init", "-q")
    env.write("a.txt", "one\ntwo\n")
    env.write("b.txt", "bee\n")
    git(env, "add", ".")
    git(env, "commit", "-q", "-m", "init")
    return env


def test_git_tools_outside_a_repo(env):
    for name in ("git_status", "git_diff"):
        r = env.call(name)
        assert not r.ok and r.error_code == ErrorCode.NOT_A_REPO
        assert r.output.startswith("Error (not_a_repo): ")


def test_git_status(repo):
    assert repo.call("git_status").output.splitlines()[0].startswith("## ")
    assert repo.call("git_status").summary == "clean"
    repo.write("a.txt", "one\nTWO\n")
    repo.write("new.txt", "n\n")
    r = repo.call("git_status")
    assert " M a.txt" in r.output and "?? new.txt" in r.output and r.metadata["changes"] == 2


def test_git_diff(repo):
    assert repo.call("git_diff").output == "No differences."
    repo.write("a.txt", "one\nTWO\n")
    out = repo.call("git_diff").output
    assert "-two" in out and "+TWO" in out and "\x1b" not in out
    assert "a.txt" in repo.call("git_diff", stat_only=True).output
    assert "-two" not in repo.call("git_diff", stat_only=True).output
    assert repo.call("git_diff", path="b.txt").output == "No differences."
    assert repo.call("git_diff", staged=True).output == "No differences."
    git(repo, "add", "a.txt")
    assert "+TWO" in repo.call("git_diff", staged=True).output


def test_git_diff_truncation_saves_log(make_env):
    env = make_env(tool_output_max_chars=800)
    git(env, "init", "-q")
    env.write("big.txt", "".join(f"row {i}\n" for i in range(500)))
    git(env, "add", ".")
    git(env, "commit", "-q", "-m", "init")
    env.write("big.txt", "".join(f"ROW {i}\n" for i in range(500)))
    r = env.call("git_diff")
    assert r.metadata["truncated"] and "[Output truncated:" in r.output
    assert (env.root / r.metadata["full_output_path"]).read_text(encoding="utf-8").count("+ROW") == 500
