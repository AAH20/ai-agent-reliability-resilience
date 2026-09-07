# AgentResilience Doctor

`agentresilience doctor` is a zero-dependency adoption and discovery command.
It statically inspects Python agent tools and highlights state-changing calls
that do not visibly carry an idempotency identifier or timeout.

```bash
agentresilience doctor path/to/agent --output doctor-report.json
```

Use `--fail-on-findings` to return exit code 2 when findings exist. This makes
the command suitable for an opt-in CI gate after the team has reviewed its
expected false positives.

## Initial rules

| Rule | Meaning |
|---|---|
| `AR001` | A state-changing call inside an agent tool has no visible idempotency identifier |
| `AR002` | A state-changing call inside an agent tool has no visible timeout or deadline |

The scanner recognizes common Python imports for OpenAI Agents, LangChain,
LangGraph, CrewAI, PydanticAI and MCP. A function is considered an agent tool
only when it has a `tool` or `function_tool` decorator. The current rules are
deliberately narrow and do not follow values across modules or prove that a
provider honors an idempotency key.

## Claim boundary

This is heuristic static inspection. A clean report is not proof of runtime
reliability, transaction safety, security or framework conformance. The next
step after discovery is an executable experiment with a negative control and
destination-state verification.
