FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY agentresilience ./agentresilience
RUN python -m pip wheel --no-deps --wheel-dir /wheels .

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 agentresilience
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels
WORKDIR /workspace
COPY --chown=agentresilience:agentresilience experiments ./experiments
USER agentresilience
ENTRYPOINT ["agentresilience"]
CMD ["run", "experiments/refund-partial-success.json", "--output", "/tmp/agent-resilience-report.json", "--brief", "/tmp/agent-resilience-report.md"]
