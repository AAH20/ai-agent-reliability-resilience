from __future__ import annotations

import ast
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


FRAMEWORK_MODULES = {
    "agents": "openai-agents",
    "crewai": "crewai",
    "langchain": "langchain",
    "langgraph": "langgraph",
    "mcp": "mcp",
    "pydantic_ai": "pydantic-ai",
}
STATE_CHANGING_CALLS = {
    "apply", "charge", "create", "delete", "deploy", "execute",
    "issue", "patch", "publish", "refund", "remove", "send", "update",
}
IDEMPOTENCY_KEYS = {"idempotency_key", "idempotencykey", "request_id", "operation_id"}
TIMEOUT_KEYS = {"timeout", "timeout_ms", "deadline"}
IGNORED_PARTS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__"}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    path: str
    line: int
    call: str
    message: str


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        parts = [node.func.attr]
        value = node.func.value
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if isinstance(value, ast.Name):
            parts.append(value.id)
        return ".".join(reversed(parts))
    return "<dynamic>"


class SourceVisitor(ast.NodeVisitor):
    def __init__(self, relative_path: str):
        self.relative_path = relative_path
        self.frameworks: set[str] = set()
        self.findings: list[Finding] = []
        self.tool_depth = 0

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root in FRAMEWORK_MODULES:
                self.frameworks.add(FRAMEWORK_MODULES[root])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        root = (node.module or "").split(".")[0]
        if root in FRAMEWORK_MODULES:
            self.frameworks.add(FRAMEWORK_MODULES[root])

    def _is_tool(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        names = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                names.append(_call_name(decorator))
            elif isinstance(decorator, ast.Name):
                names.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                names.append(decorator.attr)
        return any(name.split(".")[-1] in {"tool", "function_tool"} for name in names)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        is_tool = self._is_tool(node)
        self.tool_depth += int(is_tool)
        self.generic_visit(node)
        self.tool_depth -= int(is_tool)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)
        method = name.split(".")[-1].lower()
        if self.tool_depth and method in STATE_CHANGING_CALLS:
            keywords = {keyword.arg.lower() for keyword in node.keywords if keyword.arg}
            if not keywords & IDEMPOTENCY_KEYS:
                self.findings.append(Finding(
                    "AR001", "medium", self.relative_path, node.lineno, name,
                    "State-changing call in an agent tool has no visible idempotency identifier.",
                ))
            if not keywords & TIMEOUT_KEYS:
                self.findings.append(Finding(
                    "AR002", "medium", self.relative_path, node.lineno, name,
                    "State-changing call in an agent tool has no visible timeout or deadline.",
                ))
        self.generic_visit(node)


def scan(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ValueError(f"scan path is not a directory: {root_path}")
    frameworks: set[str] = set()
    findings: list[Finding] = []
    parse_errors: list[dict[str, Any]] = []
    scanned = 0
    for path in sorted(root_path.rglob("*.py")):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        relative = str(path.relative_to(root_path))
        try:
            tree = ast.parse(path.read_text(), filename=relative)
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            parse_errors.append({"path": relative, "error": type(exc).__name__})
            continue
        scanned += 1
        visitor = SourceVisitor(relative)
        visitor.visit(tree)
        frameworks.update(visitor.frameworks)
        findings.extend(visitor.findings)
    serialized = [asdict(finding) for finding in findings]
    fingerprint = hashlib.sha256(
        "\n".join(
            f"{item['rule_id']}:{item['path']}:{item['line']}:{item['call']}"
            for item in serialized
        ).encode()
    ).hexdigest()
    return {
        "schema_version": "1.0",
        "scan_root": root_path.name,
        "python_files_scanned": scanned,
        "frameworks_detected": sorted(frameworks),
        "findings": serialized,
        "finding_count": len(serialized),
        "parse_errors": parse_errors,
        "fingerprint_sha256": fingerprint,
        "claim_boundary": (
            "Heuristic static inspection only. Absence of findings is not proof of runtime "
            "reliability, transaction safety, security, or framework conformance."
        ),
    }
