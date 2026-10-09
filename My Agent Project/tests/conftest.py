import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_v3.approvals import ApprovalGateway, ApprovalRequest, ApprovalResult, Decision  # noqa: E402
from agent_v3.config import AgentConfig  # noqa: E402
from agent_v3.tools import build_registry  # noqa: E402
from agent_v3.tools.registry import ToolContext, ToolResult  # noqa: E402
from agent_v3.workspace import CancelToken, FileState, WorkspacePolicy  # noqa: E402


class Env:
    """A temp workspace plus everything needed to call tools the way the executor does."""

    def __init__(self, root: Path, **cfg):
        self.root = root.resolve()
        self.config = AgentConfig(workspace=self.root, **cfg)
        self.registry = build_registry()
        self.files = FileState()
        self.cancel = CancelToken()
        self.requests: list[ApprovalRequest] = []
        self.decision = ApprovalResult(Decision.ALLOW)
        self.approvals = ApprovalGateway(self._decide)
        self.seen_reads: dict = {}
        self.turn_id = "t1"
        self._calls = 0

    def _decide(self, req: ApprovalRequest) -> ApprovalResult:
        self.requests.append(req)
        return self.decision

    def reject(self, feedback=None):
        self.decision = ApprovalResult(Decision.REJECT, feedback)

    def ctx(self) -> ToolContext:
        self._calls += 1
        return ToolContext(config=self.config, workspace=WorkspacePolicy(self.root), files=self.files,
                           approvals=self.approvals, cancel=self.cancel, turn_id=self.turn_id,
                           call_id=f"c{self._calls}", seen_reads=self.seen_reads, call_index=self._calls)

    def call(self, name: str, **args) -> ToolResult:
        spec = self.registry.get(name)
        return spec.func(spec.args_model.model_validate(args), self.ctx())

    def write(self, rel: str, content, newline=None) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return p

    def read(self, rel: str) -> bytes:
        return (self.root / rel).read_bytes()


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    return Env(root)


@pytest.fixture
def make_env(tmp_path):
    def make(**cfg):
        root = tmp_path / "ws"
        root.mkdir(exist_ok=True)
        return Env(root, **cfg)
    return make


def to_json(**kw) -> str:
    return json.dumps(kw)
