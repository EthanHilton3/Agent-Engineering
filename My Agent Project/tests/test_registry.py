import json

from pydantic import BaseModel, Field

from agent_v3.tools import build_registry
from agent_v3.tools.executor import ToolCall, ToolExecutor
from agent_v3.tools.registry import ErrorCode, ToolRegistry, ToolResult, ToolSpec, strict_schema

NINE_TOOLS = ["list_dir", "glob_files", "read_file", "search_text", "edit_files", "write_file",
              "run_command", "git_status", "git_diff"]


def walk_objects(schema, path="$"):
    """Yield (path, node) for every object schema, including nested ones and anyOf branches."""
    if not isinstance(schema, dict):
        return
    if schema.get("type") == "object":
        yield path, schema
        for name, sub in schema.get("properties", {}).items():
            yield from walk_objects(sub, f"{path}.{name}")
    if "items" in schema:
        yield from walk_objects(schema["items"], path + "[]")
    for i, branch in enumerate(schema.get("anyOf", [])):
        yield from walk_objects(branch, f"{path}|{i}")


def all_keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            if k != "properties":
                yield from all_keys(v)
            else:
                for sub in v.values():
                    yield from all_keys(sub)
    elif isinstance(node, list):
        for v in node:
            yield from all_keys(v)


def test_registry_has_the_nine_tools_in_order():
    reg = build_registry()
    assert reg.names() == NINE_TOOLS
    assert {n for n in reg.names() if reg.get(n).read_only} == {
        "list_dir", "glob_files", "read_file", "search_text", "git_status", "git_diff"}


def test_schemas_are_strict_function_tools():
    for tool in build_registry().schemas():
        assert tool["type"] == "function" and tool["strict"] is True
        assert tool["description"]
        params = tool["parameters"]
        assert params["type"] == "object"
        for path, obj in walk_objects(params):
            props = obj.get("properties", {})
            assert obj["additionalProperties"] is False, (tool["name"], path)
            assert sorted(obj["required"]) == sorted(props), (tool["name"], path)
        forbidden = {"$ref", "$defs", "title", "default"} & set(all_keys(params))
        assert not forbidden, (tool["name"], forbidden)


def test_every_property_has_a_description():
    for tool in build_registry().schemas():
        for path, obj in walk_objects(tool["parameters"]):
            for name, sub in obj.get("properties", {}).items():
                assert sub.get("description", "").strip(), (tool["name"], path, name)


def test_optional_parameters_are_nullable():
    params = {t["name"]: t["parameters"] for t in build_registry().schemas()}
    start_line = params["read_file"]["properties"]["start_line"]
    assert {"type": "null"} in start_line["anyOf"]
    assert start_line["anyOf"][0] == {"type": "integer", "minimum": 1}
    assert {"type": "null"} in params["edit_files"]["properties"]["edits"]["items"]["properties"]["replace_all"]["anyOf"]
    assert "anyOf" not in params["read_file"]["properties"]["path"]


def test_nested_edit_object_is_strict():
    edits = {t["name"]: t["parameters"] for t in build_registry().schemas()}["edit_files"]["properties"]["edits"]
    assert edits["type"] == "array"
    item = edits["items"]
    assert item["additionalProperties"] is False
    assert item["required"] == ["path", "old_text", "new_text", "replace_all"]


def test_strict_schema_inlines_defs_and_drops_titles():
    class Inner(BaseModel):
        x: int = Field(description="x")

    class Outer(BaseModel):
        inner: Inner = Field(description="inner")
        many: list[Inner] = Field(description="many")

    schema = strict_schema(Outer)
    assert schema["properties"]["inner"]["properties"]["x"]["type"] == "integer"
    assert schema["properties"]["many"]["items"]["additionalProperties"] is False
    assert "$defs" not in json.dumps(schema) and "title" not in json.dumps(schema)


# --- validation path: errors, and the tool is never executed ------------------------------------

class CountArgs(BaseModel):
    n: int = Field(description="A number.")


def make_executor(calls_log, ok=True):
    def func(args, ctx):
        calls_log.append(args.n)
        return ToolResult.success("ran", "ran") if ok else ToolResult.failure(ErrorCode.NOT_FOUND, f"boom {args.n}")

    from agent_v3.config import AgentConfig
    reg = ToolRegistry([ToolSpec("count", CountArgs, func, True, "counts")])
    return ToolExecutor(reg, AgentConfig())


def run(executor, env, name, arguments):
    [(_, result, _)] = executor.run_batch([ToolCall("c1", name, arguments)], env.ctx())
    return result


def test_unknown_tool(env):
    ex = make_executor([])
    r = run(ex, env, "nope", "{}")
    assert not r.ok and r.error_code == ErrorCode.UNKNOWN_TOOL
    assert r.output.startswith("Error (unknown_tool): No tool named 'nope'. Available: count")


def test_invalid_json_is_not_executed(env):
    log = []
    r = run(make_executor(log), env, "count", '{"n": 1,, ' + "x" * 300)
    assert r.error_code == ErrorCode.INVALID_ARGUMENTS
    assert r.output.startswith("Error (invalid_arguments): ")
    # Only the first 200 chars of the raw arguments are echoed: 10 chars of JSON + 190 x's.
    assert '{"n": 1,, ' in r.output and "x" * 190 in r.output and "x" * 191 not in r.output
    assert log == []


def test_validation_errors_listed_per_field_and_not_executed(env):
    log = []
    ex = make_executor(log)
    r = run(ex, env, "count", json.dumps({"n": "abc"}))
    assert r.error_code == ErrorCode.INVALID_ARGUMENTS and "n: " in r.output
    r = run(ex, env, "count", "{}")
    assert r.error_code == ErrorCode.INVALID_ARGUMENTS and "n: Field required" in r.output
    assert log == []


def test_empty_object_is_an_error_not_silently_accepted(env):
    # v2 turned malformed JSON into {} and ran the tool anyway.
    log = []
    assert run(make_executor(log), env, "count", "not json").error_code == ErrorCode.INVALID_ARGUMENTS
    assert log == []


def test_tool_exception_becomes_internal_error(env):
    from agent_v3.config import AgentConfig

    def func(args, ctx):
        raise KeyError("oops")

    ex = ToolExecutor(ToolRegistry([ToolSpec("count", CountArgs, func, True, "c")]), AgentConfig())
    r = run(ex, env, "count", '{"n": 1}')
    assert r.error_code == ErrorCode.INTERNAL and "KeyError: 'oops'" in r.output


def test_repeated_identical_failure_is_blocked(env):
    log = []
    ex = make_executor(log, ok=False)
    first = run(ex, env, "count", '{"n": 1}')
    assert first.error_code == ErrorCode.NOT_FOUND
    again = run(ex, env, "count", '{ "n" : 1 }')          # same args, different spelling
    assert again.error_code == ErrorCode.REPEATED_FAILURE
    assert "boom 1" in again.output and "Change the arguments or approach" in again.output
    assert run(ex, env, "count", '{"n": 2}').error_code == ErrorCode.NOT_FOUND   # different args run
    assert log == [1, 2]


def test_repeated_failure_memory_is_per_turn(env):
    log = []
    ex = make_executor(log, ok=False)
    run(ex, env, "count", '{"n": 1}')
    env.turn_id = "t2"
    assert run(ex, env, "count", '{"n": 1}').error_code == ErrorCode.NOT_FOUND
    assert log == [1, 1]


def test_rejections_and_nonzero_exit_are_not_repeat_guarded(env):
    from agent_v3.config import AgentConfig
    log = []

    def func(args, ctx):
        log.append(args.n)
        return ToolResult.failure(ErrorCode.REJECTED if args.n == 1 else ErrorCode.NONZERO_EXIT, "x")

    ex = ToolExecutor(ToolRegistry([ToolSpec("count", CountArgs, func, True, "c")]), AgentConfig())
    for n in (1, 1, 2, 2):
        run(ex, env, "count", json.dumps({"n": n}))
    assert log == [1, 1, 2, 2]


def test_successful_write_clears_failure_memory(env):
    from agent_v3.config import AgentConfig
    state = {"exists": False}

    def read(args, ctx):
        return ToolResult.success("ok", "ok") if state["exists"] else ToolResult.failure(ErrorCode.NOT_FOUND, "missing")

    def write(args, ctx):
        state["exists"] = True
        return ToolResult.success("made", "made")

    reg = ToolRegistry([ToolSpec("read", CountArgs, read, True, "r"), ToolSpec("write", CountArgs, write, False, "w")])
    ex = ToolExecutor(reg, AgentConfig())
    assert run(ex, env, "read", '{"n": 1}').error_code == ErrorCode.NOT_FOUND
    assert run(ex, env, "write", '{"n": 1}').ok
    assert run(ex, env, "read", '{"n": 1}').ok
