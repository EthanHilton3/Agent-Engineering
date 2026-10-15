from agent_v3.tools.registry import ErrorCode
from agent_v3.workspace import sha12

STORE = (
    "class Store:\n"
    "    def total_value(self):\n"
    "        return sum(i.price for i in self.items)\n"
    "\n"
    "    def low_stock(self, threshold):\n"
    "        return [i for i in self.items if i.qty < threshold]\n"
)


def E(path, old, new, replace_all=None):
    return {"path": path, "old_text": old, "new_text": new, "replace_all": replace_all}


def edit(env, *edits):
    return env.call("edit_files", edits=list(edits))


# --- exact edits ---------------------------------------------------------------------------------

def test_single_exact_edit(env):
    env.write("store.py", STORE)
    r = edit(env, E("store.py", "i.price for", "i.price * i.qty for"))
    assert r.ok, r.output
    assert env.read("store.py").decode() == STORE.replace("i.price for", "i.price * i.qty for")
    sha = sha12(env.read("store.py"))
    assert r.output == f"Edited 1 file:\n  store.py  +1 −1  lines 3–3  sha {sha}"
    assert r.metadata["files_changed"] == [{"path": "store.py", "added": 1, "removed": 1}]
    assert r.metadata["sha"] == sha and r.metadata["line_range"] == [3, 3]
    assert env.files.get(env.root / "store.py") == sha


def test_approval_request_carries_diff_and_paths(env):
    env.write("store.py", STORE)
    edit(env, E("store.py", "(self, threshold)", "(self, limit)"))
    [req] = env.requests
    assert req.kind == "edit" and req.title == "Edit 1 file" and not req.outside_workspace
    assert req.paths == [str(env.root / "store.py")]
    assert "--- a/store.py" in req.diff and "+++ b/store.py" in req.diff
    assert "-    def low_stock(self, threshold):" in req.diff and "+    def low_stock(self, limit):" in req.diff


def test_multi_file_edit_in_one_call_and_one_approval(env):
    env.write("a.py", "x = 1\ny = 2\n")
    env.write("sub/b.py", "def f():\n    return 1\n")
    r = edit(env, E("a.py", "x = 1", "x = 10"), E("sub/b.py", "return 1", "return 2\n    # done"))
    assert r.ok
    assert env.read("a.py") == b"x = 10\ny = 2\n"
    assert env.read("sub/b.py") == b"def f():\n    return 2\n    # done\n"
    assert r.output.startswith("Edited 2 files:\n  a.py  +1 −1") and "  sub/b.py  +2 −1" in r.output
    assert len(env.requests) == 1 and env.requests[0].title == "Edit 2 files"
    assert len(env.requests[0].paths) == 2


def test_edits_to_same_file_apply_in_order(env):
    env.write("a.py", "one\n")
    r = edit(env, E("a.py", "one", "two"), E("a.py", "two", "three"))
    assert r.ok and env.read("a.py") == b"three\n"


def test_line_range_and_counts(env):
    env.write("big.txt", "".join(f"line {i}\n" for i in range(1, 51)))
    r = edit(env, E("big.txt", "line 40\nline 41", "a\nb\nc\nd"))
    assert "+4 −2  lines 40–43" in r.output and r.summary == "1 file +4 −2"


def test_replace_all(env):
    env.write("a.py", "foo\nbar\nfoo\n")
    r = edit(env, E("a.py", "foo", "baz", replace_all=True))
    assert r.ok and env.read("a.py") == b"baz\nbar\nbaz\n"


def test_ambiguous_lists_line_numbers_and_writes_nothing(env):
    original = "foo\nbar\nfoo\nbaz\nfoo\n"
    env.write("a.py", original)
    r = edit(env, E("a.py", "foo", "qux"))
    assert not r.ok and r.error_code == ErrorCode.AMBIGUOUS
    assert "lines 1, 3, 5" in r.output and "replace_all" in r.output
    assert env.read("a.py").decode() == original and env.requests == []


def test_ambiguous_lists_at_most_five_lines(env):
    env.write("a.py", "foo\n" * 8)
    r = edit(env, E("a.py", "foo", "x"))
    assert "lines 1, 2, 3, 4, 5, …" in r.output and "8 places" in r.output


def test_no_change_edit_asks_for_nothing(env):
    env.write("a.py", "x\n")
    r = edit(env, E("a.py", "x", "x"))
    assert r.ok and "(no change)" in r.output and env.requests == []


def test_empty_old_text_rejected(env):
    env.write("a.py", "x\n")
    r = edit(env, E("a.py", "", "y"))
    assert r.error_code == ErrorCode.INVALID_ARGUMENTS


# --- lenient matching ----------------------------------------------------------------------------

def test_trailing_whitespace_lenient(env):
    env.write("a.py", "def f():  \n    return 1\t\n")
    r = edit(env, E("a.py", "def f():\n    return 1", "def f():\n    return 2"))
    assert r.ok, r.output
    assert env.read("a.py") == b"def f():\n    return 2\n"
    assert "Note: edit 1 matched after ignoring trailing whitespace." in r.output


def test_lenient_can_be_disabled(make_env):
    env = make_env(lenient_edit_match=False)
    env.write("a.py", "def f():  \n    return 1\n")
    r = edit(env, E("a.py", "def f():\n    return 1", "x"))
    assert r.error_code == ErrorCode.NO_MATCH
    assert env.read("a.py") == b"def f():  \n    return 1\n"


def test_tabs_vs_spaces_uniform_indent_with_reindented_new_text(env):
    env.write("a.py", "class A:\n\tdef f(self):\n\t\treturn 1\n")
    old = "    def f(self):\n        return 1"
    new = "    def f(self):\n        x = 2\n        return x"
    r = edit(env, E("a.py", old, new))
    assert r.ok, r.output
    assert env.read("a.py") == b"class A:\n\tdef f(self):\n\t\tx = 2\n\t\treturn x\n"
    assert "Note: edit 1 matched after ignoring indentation differences." in r.output


def test_single_line_indent_change(env):
    env.write("a.py", "        value = compute()\n")
    r = edit(env, E("a.py", "    value = compute()", "    value = other()"))
    assert r.ok and env.read("a.py") == b"        value = other()\n"


def test_non_uniform_indent_is_rejected(env):
    original = "\tdef f(self):\n\t\t\t\treturn 1\n"
    env.write("a.py", original)
    # Model dedented the first line by 4 spaces but the second by 2 relative to the file: not one uniform change.
    r = edit(env, E("a.py", "    def f(self):\n  return 1", "    def f(self):\n  return 2"))
    assert r.error_code == ErrorCode.NO_MATCH
    assert env.read("a.py").decode() == original


def test_new_text_that_cannot_be_reindented_is_rejected(env):
    original = "\t\t\tfoo()\n"
    env.write("a.py", original)
    r = edit(env, E("a.py", "    foo()", "bar()"))      # new_text is shallower than old_text's indent
    assert r.error_code == ErrorCode.NO_MATCH and env.read("a.py").decode() == original


def test_lenient_match_must_be_unique(env):
    env.write("a.py", "x = 1  \nother\nx = 1\t\n")
    r = edit(env, E("a.py", "x = 1\n", "x = 2\n"))       # no exact match, two whitespace-insensitive ones
    assert r.error_code == ErrorCode.AMBIGUOUS and "lines 1, 3" in r.output


# --- no match / closest snippet ------------------------------------------------------------------

def test_no_match_includes_closest_snippet(env):
    env.write("store.py", STORE)
    r = edit(env, E("store.py", "    def total_value(self):\n        return sum(i.price for i in self.item)",
                    "x"))
    assert not r.ok and r.error_code == ErrorCode.NO_MATCH
    assert "Closest match at lines 2–3 (similarity " in r.output
    assert "2|     def total_value(self):" in r.output
    assert "3|         return sum(i.price for i in self.items)" in r.output


def test_no_match_without_similar_text(env):
    env.write("store.py", STORE)
    r = edit(env, E("store.py", "completely_unrelated_symbol_xyz = 12345", "x"))
    assert r.error_code == ErrorCode.NO_MATCH
    assert "Closest match" not in r.output and "No similar text found" in r.output


def test_closest_snippet_is_capped_at_30_lines(env):
    body = "".join(f"    statement_number_{i} = {i}\n" for i in range(100))
    env.write("big.py", body)
    old = "".join(f"    statement_number_{i} = {i + 1}\n" for i in range(40))
    r = edit(env, E("big.py", old, "x"))
    assert "Closest match at lines 1–30" in r.output
    assert r.output.count("statement_number_") == 30


# --- all-or-nothing ------------------------------------------------------------------------------

def test_partial_failure_writes_nothing_and_lists_each_failure(env):
    env.write("a.py", "alpha\n")
    env.write("b.py", "beta\nbeta\n")
    r = edit(env, E("a.py", "alpha", "ALPHA"), E("b.py", "beta", "BETA"), E("a.py", "missing", "x"))
    assert not r.ok
    assert env.read("a.py") == b"alpha\n" and env.read("b.py") == b"beta\nbeta\n"
    assert "2 edits failed; no files were changed." in r.output
    assert "edit 2 (b.py):" in r.output and "edit 3 (a.py):" in r.output
    assert env.requests == []                              # nothing to approve, nothing written


def test_missing_binary_and_directory_targets(env):
    env.write("blob.bin", b"\x00\x01")
    (env.root / "d").mkdir()
    env.write("ok.py", "x\n")
    r = edit(env, E("nope.py", "a", "b"), E("blob.bin", "a", "b"), E("d", "a", "b"), E("ok.py", "x", "y"))
    assert "edit 1 (nope.py): nope.py does not exist" in r.output
    assert "edit 2 (blob.bin)" in r.output and "edit 3 (d)" in r.output
    assert r.error_code == ErrorCode.NOT_FOUND
    assert env.read("ok.py") == b"x\n"


# --- line endings, BOM, trailing newline ---------------------------------------------------------

def test_crlf_preserved(env):
    env.write("w.txt", b"one\r\ntwo\r\nthree\r\n")
    r = edit(env, E("w.txt", "two\nthree", "TWO\nTHREE\nFOUR"))
    assert r.ok, r.output
    assert env.read("w.txt") == b"one\r\nTWO\r\nTHREE\r\nFOUR\r\n"


def test_mixed_endings_keep_untouched_lines_and_new_lines_use_the_majority(env):
    env.write("lf.txt", b"a\nb\nc\r\nd\n")
    assert edit(env, E("lf.txt", "b", "B\nB2")).ok
    assert env.read("lf.txt") == b"a\nB\nB2\nc\r\nd\n"
    env.write("crlf.txt", b"a\r\nb\r\nc\nd\r\n")
    r = edit(env, E("crlf.txt", "b", "B\nB2"))
    assert r.ok and r.metadata["files_changed"] == [{"path": "crlf.txt", "added": 2, "removed": 1}]
    assert env.read("crlf.txt") == b"a\r\nB\r\nB2\r\nc\nd\r\n"


def test_crlf_in_model_text_still_matches(env):
    env.write("w.txt", b"one\r\ntwo\r\n")
    assert edit(env, E("w.txt", "one\r\ntwo", "1\r\n2")).ok
    assert env.read("w.txt") == b"1\r\n2\r\n"


def test_lf_file_stays_lf(env):
    env.write("u.txt", b"one\ntwo\n")
    edit(env, E("u.txt", "two", "2"))
    assert env.read("u.txt") == b"one\n2\n"


def test_no_trailing_newline_preserved(env):
    env.write("n.txt", b"one\ntwo")
    assert edit(env, E("n.txt", "two", "three\nfour")).ok
    assert env.read("n.txt") == b"one\nthree\nfour"


def test_trailing_newline_preserved_when_edit_swallows_it(env):
    env.write("n.txt", b"one\ntwo\n")
    assert edit(env, E("n.txt", "two\n", "three")).ok
    assert env.read("n.txt") == b"one\nthree\n"


def test_bom_preserved(env):
    env.write("b.txt", b"\xef\xbb\xbfhello\nworld\n")
    assert edit(env, E("b.txt", "world", "there")).ok
    assert env.read("b.txt") == b"\xef\xbb\xbfhello\nthere\n"


def test_non_ascii_round_trip(env):
    env.write("u.txt", "café ☕\nnaïve\n")
    assert edit(env, E("u.txt", "naïve", "naïve ✓")).ok
    assert env.read("u.txt").decode("utf-8") == "café ☕\nnaïve ✓\n"


def test_no_temp_file_left_behind(env):
    env.write("a.py", "x\n")
    edit(env, E("a.py", "x", "y"))
    assert sorted(p.name for p in env.root.iterdir()) == ["a.py"]


# --- stale checks --------------------------------------------------------------------------------

def test_stale_sha_conflict_after_external_change(env):
    p = env.write("report.py", STORE)
    env.call("read_file", path="report.py")
    p.write_bytes((STORE + "# changed outside\n").encode())
    r = edit(env, E("report.py", "threshold", "limit"))
    assert r.error_code == ErrorCode.CONFLICT
    assert "report.py changed since you last read it (sha " in r.output and "→" in r.output
    assert "Re-read the region you are editing." in r.output
    assert "threshold" in env.read("report.py").decode() and env.requests == []


def test_unread_file_may_be_edited_without_conflict(env):
    env.write("a.py", "x = 1\n")
    assert edit(env, E("a.py", "x = 1", "x = 2")).ok


def test_agent_can_chain_edits_without_rereading(env):
    env.write("a.py", "x = 1\n")
    env.call("read_file", path="a.py")
    assert edit(env, E("a.py", "x = 1", "x = 2")).ok
    assert edit(env, E("a.py", "x = 2", "x = 3")).ok          # FileState was updated by the first edit
    assert env.read("a.py") == b"x = 3\n"


def test_file_changed_during_approval_wait_is_a_conflict(env):
    p = env.write("a.py", "x = 1\n")

    def decide(req):
        p.write_bytes(b"x = 99\n")                            # user edits the file while the prompt is open
        return env.decision

    env.approvals._decide = decide
    r = edit(env, E("a.py", "x = 1", "x = 2"))
    assert r.error_code == ErrorCode.CONFLICT and "while waiting for approval" in r.output
    assert env.read("a.py") == b"x = 99\n"


# --- approvals -----------------------------------------------------------------------------------

def test_rejection_writes_nothing(env):
    env.write("a.py", "x = 1\n")
    env.reject()
    r = edit(env, E("a.py", "x = 1", "x = 2"))
    assert not r.ok and r.error_code == ErrorCode.REJECTED
    assert r.output == "Error (rejected): The user rejected this edit."
    assert env.read("a.py") == b"x = 1\n" and sorted(p.name for p in env.root.iterdir()) == ["a.py"]


def test_rejection_feedback_reaches_the_model(env):
    env.write("a.py", "x = 1\n")
    env.reject("keep the old name")
    r = edit(env, E("a.py", "x = 1", "x = 2"))
    assert r.output == "Error (rejected): The user rejected this edit.\nUser feedback: keep the old name"


def test_default_gateway_rejects(env):
    from agent_v3.approvals import ApprovalGateway
    env.approvals = ApprovalGateway()
    env.write("a.py", "x\n")
    assert edit(env, E("a.py", "x", "y")).error_code == ErrorCode.REJECTED
    assert env.read("a.py") == b"x\n"


def test_edit_outside_workspace_requests_approval_flagged(env, tmp_path):
    outside = tmp_path / "elsewhere.txt"
    outside.write_text("old\n", encoding="utf-8")
    r = edit(env, E(str(outside), "old", "new"))
    assert r.ok and outside.read_text(encoding="utf-8") == "new\n"
    [req] = env.requests
    assert req.outside_workspace is True and req.reason == "write outside workspace"
    assert str(outside) in req.diff


def test_edit_outside_workspace_rejected_writes_nothing(env, tmp_path):
    outside = tmp_path / "elsewhere.txt"
    outside.write_text("old\n", encoding="utf-8")
    env.reject()
    assert edit(env, E("../elsewhere.txt", "old", "new")).error_code == ErrorCode.REJECTED
    assert outside.read_text(encoding="utf-8") == "old\n"


# --- write_file ----------------------------------------------------------------------------------

def test_write_creates_file_and_parents(env):
    r = env.call("write_file", path="tests/new/test_count.py", content="a\nb\nc\n")
    sha = sha12(b"a\nb\nc\n")
    assert r.ok and r.output == f"Created tests/new/test_count.py (3 lines, sha {sha})"
    assert env.read("tests/new/test_count.py") == b"a\nb\nc\n"
    [req] = env.requests
    assert req.kind == "edit" and req.title == "Create file" and "+a" in req.diff
    assert req.metadata["full_content"] == "a\nb\nc\n"
    assert env.files.get(env.root / "tests/new/test_count.py") == sha


def test_write_create_diff_is_first_40_lines_with_full_content_available(env):
    content = "".join(f"l{i}\n" for i in range(100))
    env.call("write_file", path="big.txt", content=content)
    [req] = env.requests
    assert req.diff.count("\n+l") == 40 and "… 60 more lines" in req.diff
    assert req.metadata["full_content"] == content


def test_write_existing_without_overwrite_conflicts(env):
    env.write("a.txt", "old\n")
    r = env.call("write_file", path="a.txt", content="new\n")
    assert r.error_code == ErrorCode.CONFLICT
    assert r.output == "Error (conflict): File exists. Use edit_files, or set overwrite=true after reading it."
    assert env.read("a.txt") == b"old\n" and env.requests == []


def test_write_overwrite_requires_prior_read(env):
    env.write("a.txt", "old\n")
    r = env.call("write_file", path="a.txt", content="new\n", overwrite=True)
    assert r.error_code == ErrorCode.CONFLICT and "Read the current file before overwriting it." in r.output
    assert env.read("a.txt") == b"old\n"


def test_write_overwrite_after_read(env):
    env.write("a.txt", "one\ntwo\nthree\n")
    env.call("read_file", path="a.txt")
    r = env.call("write_file", path="a.txt", content="one\n2\n3\n4\n", overwrite=True)
    assert r.ok and r.output.startswith("Overwrote a.txt (+3 −2, sha ")
    assert env.read("a.txt") == b"one\n2\n3\n4\n"
    assert "-two" in env.requests[0].diff and "+2" in env.requests[0].diff
    assert env.requests[0].title == "Overwrite file"


def test_write_overwrite_with_stale_sha_conflicts(env):
    p = env.write("a.txt", "one\n")
    env.call("read_file", path="a.txt")
    p.write_bytes(b"changed\n")
    r = env.call("write_file", path="a.txt", content="new\n", overwrite=True)
    assert r.error_code == ErrorCode.CONFLICT and "Read the current file" in r.output
    assert env.read("a.txt") == b"changed\n"


def test_write_overwrite_preserves_crlf_and_bom(env):
    env.write("w.txt", b"\xef\xbb\xbfone\r\ntwo\r\n")
    env.call("read_file", path="w.txt")
    assert env.call("write_file", path="w.txt", content="x\ny\nz\n", overwrite=True).ok
    assert env.read("w.txt") == b"\xef\xbb\xbfx\r\ny\r\nz\r\n"


def test_write_overwrite_keeps_mixed_endings_of_unchanged_lines(env):
    env.write("m.txt", b"one\r\ntwo\nthree\r\nfour\r\n")
    env.call("read_file", path="m.txt")
    assert env.call("write_file", path="m.txt", content="one\ntwo\nTHREE\nfour\nfive\n", overwrite=True).ok
    assert env.read("m.txt") == b"one\r\ntwo\nTHREE\r\nfour\r\nfive\r\n"


def test_write_new_file_keeps_content_as_given(env):
    env.call("write_file", path="n.txt", content="a\nb")
    assert env.read("n.txt") == b"a\nb"


def test_write_rejection_writes_nothing(env):
    env.reject("no")
    r = env.call("write_file", path="sub/a.txt", content="x\n")
    assert r.error_code == ErrorCode.REJECTED and "User feedback: no" in r.output
    assert not (env.root / "sub").exists()


def test_write_outside_workspace_flagged(env, tmp_path):
    target = tmp_path / "out.txt"
    r = env.call("write_file", path=str(target), content="x\n")
    assert r.ok and r.metadata["outside_workspace"] is True
    assert env.requests[0].outside_workspace and env.requests[0].reason == "write outside workspace"


def test_write_then_edit_without_reading(env):
    env.call("write_file", path="a.py", content="x = 1\n")
    assert edit(env, E("a.py", "x = 1", "x = 2")).ok


def test_write_to_directory_path_fails(env):
    (env.root / "d").mkdir()
    assert env.call("write_file", path="d", content="x", overwrite=True).error_code == ErrorCode.INVALID_ARGUMENTS
