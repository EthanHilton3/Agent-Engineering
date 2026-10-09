import re

from agent_v3.tools.registry import ErrorCode
from agent_v3.workspace import sha12

NUMBERED = "\n".join(f"line {i}" for i in range(1, 101)) + "\n"


# --- read_file ----------------------------------------------------------------------------------

def test_read_range_and_footer(env):
    env.write("report.py", NUMBERED)
    r = env.call("read_file", path="report.py", start_line=3, end_line=5)
    sha = sha12(NUMBERED.encode())
    assert r.ok
    assert r.output == f"3| line 3\n4| line 4\n5| line 5\n[report.py · lines 3–5 of 100 · sha {sha} · next: start_line=6]"
    assert r.summary == "lines 3–5"
    assert r.metadata["line_range"] == [3, 5] and r.metadata["sha"] == sha


def test_line_numbers_are_right_aligned_not_zero_padded(env):
    env.write("a.txt", NUMBERED)
    out = env.call("read_file", path="a.txt", start_line=8, end_line=11).output.splitlines()
    assert out[:4] == [" 8| line 8", " 9| line 9", "10| line 10", "11| line 11"]


def test_footer_omits_next_at_end_of_file(env):
    content = b"one\ntwo\n"
    env.write("a.txt", content)
    r = env.call("read_file", path="a.txt")
    assert r.output.endswith(f"[a.txt · lines 1–2 of 2 · sha {sha12(content)}]")
    assert "next:" not in r.output


def test_default_range_is_capped_at_read_max_lines(make_env):
    env = make_env(read_max_lines=10)
    env.write("a.txt", NUMBERED)
    r = env.call("read_file", path="a.txt")
    assert "10| line 10" in r.output and "11| line 11" not in r.output
    assert "lines 1–10 of 100" in r.output and "next: start_line=11" in r.output
    env.seen_reads.clear()
    explicit = env.call("read_file", path="a.txt", start_line=1, end_line=50)       # explicit end is clamped too
    assert "lines 1–10 of 100" in explicit.output


def test_char_cap_cuts_at_whole_lines(make_env):
    env = make_env(read_max_chars=100)
    env.write("a.txt", "\n".join("x" * 30 for _ in range(20)) + "\n")
    r = env.call("read_file", path="a.txt")
    body = [l for l in r.output.splitlines() if "| " in l and not l.startswith("[")]
    assert 1 <= len(body) < 20
    assert all(l.endswith("x" * 30) for l in body)             # never a partial line
    assert f"next: start_line={len(body) + 1}" in r.output


def test_very_long_line_is_truncated(env):
    env.write("a.txt", "short\n" + "y" * 5000 + "\nend\n")
    r = env.call("read_file", path="a.txt")
    assert "…[line truncated, 5000 chars]" in r.output
    assert "y" * 2001 not in r.output and "y" * 2000 in r.output


def test_binary_file_rejected(env):
    env.write("blob.bin", b"abc\x00def")
    r = env.call("read_file", path="blob.bin")
    assert not r.ok and r.error_code == ErrorCode.BINARY and r.output.startswith("Error (binary): ")


def test_non_utf8_rejected(env):
    env.write("latin.txt", "café".encode("latin-1"))
    r = env.call("read_file", path="latin.txt")
    assert r.error_code == ErrorCode.BINARY and "not UTF-8 text" in r.output


def test_bom_is_stripped(env):
    env.write("bom.txt", b"\xef\xbb\xbfhello\nworld\n")
    r = env.call("read_file", path="bom.txt")
    assert r.ok and "﻿" not in r.output and "1| hello" in r.output


def test_crlf_lines_have_no_carriage_returns(env):
    env.write("w.txt", b"a\r\nb\r\n")
    r = env.call("read_file", path="w.txt")
    assert "\r" not in r.output and "1| a\n2| b\n" in r.output


def test_too_large(env):
    env.write("big.txt", b"a" * (10 * 1024 * 1024 + 1))
    r = env.call("read_file", path="big.txt")
    assert r.error_code == ErrorCode.TOO_LARGE and "search_text" in r.output


def test_missing_and_directory_and_bad_range(env):
    env.write("d/x.txt", "x\n")
    assert env.call("read_file", path="nope.txt").error_code == ErrorCode.NOT_FOUND
    assert env.call("read_file", path="d").error_code == ErrorCode.INVALID_ARGUMENTS
    assert env.call("read_file", path="d/x.txt", start_line=5).error_code == ErrorCode.INVALID_ARGUMENTS
    assert env.call("read_file", path="d/x.txt", start_line=2, end_line=1).error_code == ErrorCode.INVALID_ARGUMENTS


def test_empty_file(env):
    env.write("empty.txt", "")
    r = env.call("read_file", path="empty.txt")
    assert r.ok and "empty file" in r.output


def test_read_updates_file_state_with_whole_file_sha_even_for_partial_range(env):
    p = env.write("a.txt", NUMBERED)
    env.call("read_file", path="a.txt", start_line=1, end_line=2)
    assert env.files.get(p) == sha12(NUMBERED.encode())


def test_dedupe_hit_returns_placeholder(env):
    env.write("a.txt", NUMBERED)
    first = env.call("read_file", path="a.txt", start_line=1, end_line=5)
    second = env.call("read_file", path="a.txt", start_line=1, end_line=5)
    assert first.ok and "line 1" in first.output
    assert second.ok and second.metadata["deduped"] is True
    assert second.output.startswith("Unchanged since your earlier read of these lines (same sha ")
    assert "line 1" not in second.output


def test_dedupe_misses(env):
    p = env.write("a.txt", NUMBERED)
    env.call("read_file", path="a.txt", start_line=1, end_line=5)
    # different range
    assert "line 6" in env.call("read_file", path="a.txt", start_line=1, end_line=6).output
    # changed content → different sha → invalidated
    p.write_bytes(NUMBERED.replace("line 2\n", "LINE TWO\n").encode())
    again = env.call("read_file", path="a.txt", start_line=1, end_line=5)
    assert "deduped" not in again.metadata and "LINE TWO" in again.output


def test_dedupe_is_per_turn_cache_and_can_be_disabled(make_env):
    env = make_env()
    env.write("a.txt", NUMBERED)
    env.call("read_file", path="a.txt", end_line=3)
    env.seen_reads.clear()                        # the session hands each turn a fresh cache
    assert "deduped" not in env.call("read_file", path="a.txt", end_line=3).metadata

    off = make_env(dedupe_reads=False)
    off.call("read_file", path="a.txt", end_line=3)
    assert "deduped" not in off.call("read_file", path="a.txt", end_line=3).metadata


def test_dedupe_matches_effective_range(env):
    env.write("a.txt", "a\nb\nc\n")
    env.call("read_file", path="a.txt")                           # effective 1–3
    assert env.call("read_file", path="a.txt", start_line=1, end_line=99).metadata.get("deduped")


# --- outside workspace ---------------------------------------------------------------------------

def test_reads_outside_workspace_allowed_and_flagged(env, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "n.txt").write_text("hello\n", encoding="utf-8")
    abs_path = str(other / "n.txt")
    r = env.call("read_file", path=abs_path)
    assert r.ok and r.metadata["outside_workspace"] is True and "hello" in r.output
    assert env.call("read_file", path="../other/n.txt").metadata["outside_workspace"] is True
    assert env.call("list_dir", path=str(other)).metadata["outside_workspace"] is True
    assert env.call("glob_files", pattern="*.txt", path=str(other)).metadata["outside_workspace"] is True
    assert env.call("search_text", pattern="hello", path=str(other)).metadata["outside_workspace"] is True
    assert env.requests == []                                       # reads never ask for approval


def test_inside_workspace_is_not_flagged(env):
    env.write("a.txt", "x\n")
    assert "outside_workspace" not in env.call("read_file", path="a.txt").metadata
    assert "outside_workspace" not in env.call("read_file", path=str(env.root / "a.txt")).metadata


def test_workspace_prefix_sibling_is_outside(env):
    sibling = env.root.parent / (env.root.name + "-evil")
    sibling.mkdir()
    (sibling / "s.txt").write_text("s\n", encoding="utf-8")
    assert env.call("read_file", path=str(sibling / "s.txt")).metadata["outside_workspace"] is True


# --- list_dir ------------------------------------------------------------------------------------

def test_list_dir_folders_first_with_sizes(env):
    env.write("b.py", "x" * 3200)
    env.write("a.txt", "hi")
    env.write("zdir/f.txt", "1")
    env.write("adir/f.txt", "1")
    out = env.call("list_dir", path=".").output.splitlines()
    assert out == ["adir/", "zdir/", "a.txt  2 B", "b.py  3.1 KB"]


def test_list_dir_paging(env):
    for i in range(205):
        env.write(f"f{i:03}.txt", "x")
    first = env.call("list_dir", path=".")
    lines = first.output.splitlines()
    assert len(lines) == 201 and lines[-1] == "[Showing entries 1-200 of 205. To list more, call list_dir with offset=200.]"
    second = env.call("list_dir", path=".", offset=200).output.splitlines()
    assert second == [f"f{i:03}.txt  1 B" for i in range(200, 205)]
    assert env.call("list_dir", path=".", offset=999).error_code == ErrorCode.INVALID_ARGUMENTS


def test_list_dir_errors_and_empty(env):
    env.write("a.txt", "x")
    (env.root / "empty").mkdir()
    assert env.call("list_dir", path="empty").output == "(empty directory)"
    assert env.call("list_dir", path="a.txt").error_code == ErrorCode.INVALID_ARGUMENTS
    assert env.call("list_dir", path="missing").error_code == ErrorCode.NOT_FOUND


# --- glob_files ----------------------------------------------------------------------------------

def make_tree(env):
    for rel in ["a.py", "src/b.py", "src/pkg/c.py", "src/pkg/test_c.py", "src/test_b.py", "README.md",
                "node_modules/x/ignored.py", ".git/hooks/ignored.py", "__pycache__/z.py", "docs/guide.md"]:
        env.write(rel, "x\n")


def test_glob_recursive_sorted_and_skips_ignored(env):
    make_tree(env)
    r = env.call("glob_files", pattern="**/*.py")
    assert r.output == "a.py\nsrc/b.py\nsrc/pkg/c.py\nsrc/pkg/test_c.py\nsrc/test_b.py\n[5 files]"
    assert r.summary == "5 files"


def test_glob_pattern_variants(env):
    make_tree(env)
    assert env.call("glob_files", pattern="src/**/test_*.py").output.splitlines() == [
        "src/pkg/test_c.py", "src/test_b.py", "[2 files]"]
    assert env.call("glob_files", pattern="*.py").output.splitlines() == ["a.py", "[1 files]"]
    assert env.call("glob_files", pattern="*.md").output.splitlines() == ["README.md", "[1 files]"]
    assert env.call("glob_files", pattern="**/*.md", path="docs").output.splitlines() == ["guide.md", "[1 files]"]


def test_glob_paths_are_relative_to_search_root(env):
    make_tree(env)
    assert env.call("glob_files", pattern="**/*.py", path="src/pkg").output.splitlines() == [
        "c.py", "test_c.py", "[2 files]"]


def test_glob_caps(env):
    for i in range(30):
        env.write(f"f{i:02}.txt", "x")
    r = env.call("glob_files", pattern="*.txt", max_results=10)
    lines = r.output.splitlines()
    assert lines[-1] == "[showing 10 of 30 files]" and len(lines) == 11 and r.metadata["truncated"]
    assert env.call("glob_files", pattern="*.txt").output.splitlines()[-1] == "[30 files]"


def test_glob_path_inside_ignored_dir_is_allowed(env):
    make_tree(env)
    assert env.call("glob_files", pattern="**/*.py", path="node_modules").output.splitlines() == [
        "x/ignored.py", "[1 files]"]


def test_glob_no_matches_and_bad_path(env):
    assert env.call("glob_files", pattern="*.nothing").output == "[0 files]"
    assert env.call("glob_files", pattern="*", path="nowhere").error_code == ErrorCode.NOT_FOUND


# --- search_text ---------------------------------------------------------------------------------

STORE = "class Store:\n    def total_value(self):\n        return 1\n\n    def other(self):\n        return 2\n"


def test_search_groups_by_file_with_aligned_numbers(env):
    env.write("inventory/store.py", STORE)
    env.write("tests/test_store.py", "def test():\n    assert total_value() == 3\n")
    r = env.call("search_text", pattern="total_value")
    assert r.output == ("inventory/store.py\n"
                        "  2:     def total_value(self):\n"
                        "tests/test_store.py\n"
                        "  2:     assert total_value() == 3\n"
                        "[2 matches in 2 files]")
    assert r.metadata["matches"] == 2 and r.metadata["files"] == 2


def test_search_number_width_follows_largest_line(env):
    env.write("big.txt", "\n".join(["pad"] * 11 + ["needle"]) + "\n")
    env.write("small.txt", "needle\n")
    out = env.call("search_text", pattern="needle").output
    assert "  12: needle" in out and "   1: needle" in out


def test_search_is_fixed_string_by_default(env):
    env.write("a.txt", "a.c\nabc\n")
    assert env.call("search_text", pattern="a.c").metadata["matches"] == 1
    assert env.call("search_text", pattern="a.c", regex=True).metadata["matches"] == 2


def test_search_ignore_case_and_glob(env):
    env.write("a.py", "Hello\n")
    env.write("b.txt", "hello\n")
    assert env.call("search_text", pattern="hello").metadata["matches"] == 1
    assert env.call("search_text", pattern="hello", ignore_case=True).metadata["matches"] == 2
    r = env.call("search_text", pattern="hello", ignore_case=True, glob="*.py")
    assert r.output.splitlines()[0] == "a.py" and r.metadata["files"] == 1


def test_search_context_lines(env):
    env.write("a.txt", "\n".join(f"l{i}" for i in range(1, 21)) + "\n")
    out = env.call("search_text", pattern="l10", context_lines=1).output.splitlines()
    assert out[:4] == ["a.txt", "   9- l9", "  10: l10", "  11- l11"]
    gapped = env.call("search_text", pattern="l5", regex=True, context_lines=1).output
    assert "--" not in gapped
    both = env.call("search_text", pattern=r"l(3|8)$", regex=True, context_lines=1).output
    assert "  --" in both


def test_search_caps_matches(env):
    for i in range(5):
        env.write(f"f{i}.txt", "hit\nhit\nhit\n")
    r = env.call("search_text", pattern="hit", max_results=4)
    assert r.output.splitlines()[-1] == "[showing 4 of 15 matches in 5 files — narrow with path or glob]"
    assert r.output.count(": hit") == 4 and r.metadata["truncated"]


def test_search_output_respects_char_budget(make_env):
    env = make_env(tool_output_max_chars=500)
    env.write("a.txt", ("x" * 150 + " hit\n") * 100)
    r = env.call("search_text", pattern="hit", max_results=300)
    assert len(r.output) < 1500 and "showing" in r.output.splitlines()[-1]


def test_search_truncates_long_lines(env):
    env.write("a.txt", "hit " + "z" * 500 + "\n")
    line = env.call("search_text", pattern="hit").output.splitlines()[1]
    assert line.endswith("…") and len(line) < 220


def test_search_skips_ignored_dirs_binary_and_large(env):
    env.write("keep.txt", "needle\n")
    env.write("node_modules/m.txt", "needle\n")
    env.write(".git/c.txt", "needle\n")
    env.write("__pycache__/p.txt", "needle\n")
    env.write("bin.dat", b"needle\x00\x01")
    env.write("huge.txt", b"needle\n" + b"a" * (2 * 1024 * 1024 + 10))
    r = env.call("search_text", pattern="needle")
    assert r.output.splitlines() == ["keep.txt", "  1: needle", "[1 match in 1 file]"]


def test_search_inside_an_ignored_dir_when_pointed_at_it(env):
    env.write(".agent_v3/outputs/t1_0.log", "line\nFAILED test_x\n")
    r = env.call("search_text", pattern="FAILED", path=".agent_v3/outputs/t1_0.log")
    assert r.ok and r.metadata["matches"] == 1
    r = env.call("search_text", pattern="FAILED", path=".agent_v3")
    assert r.metadata["matches"] == 1


def test_search_single_file_path_shows_file_name(env):
    env.write("sub/a.txt", "hit\n")
    assert env.call("search_text", pattern="hit", path="sub/a.txt").output.splitlines()[0] == "a.txt"


def test_search_errors_and_no_match(env):
    env.write("a.txt", "x\n")
    assert env.call("search_text", pattern="(", regex=True).error_code == ErrorCode.INVALID_ARGUMENTS
    assert env.call("search_text", pattern="x", path="nope").error_code == ErrorCode.NOT_FOUND
    r = env.call("search_text", pattern="zzz")
    assert r.ok and r.metadata["matches"] == 0 and re.search(r"0 matches", r.output)
