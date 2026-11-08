# Sandbox image for my agent_v3. The only things inside are the agent code and a toy project.
# Nothing from my real disk is mounted, so whatever the agent breaks, it breaks in here.
# Before building, copy agent_v3/ in from my private my-agent repo (it's left out of this public repo).
FROM python:3.12-slim

RUN pip install --no-cache-dir openai httpx pydantic rich \
 && useradd --create-home agent

COPY agent_v3 /opt/agent/agent_v3
COPY fake_project /work
RUN chown -R agent:agent /work

USER agent
WORKDIR /work
ENV PYTHONPATH=/opt/agent PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "agent_v3", "--workspace", "/work", "--no-save", "--no-web"]
