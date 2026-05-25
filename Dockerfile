# Calibrated Readiness - container image.
#
# Default build runs the verifiable core only, so `docker run` always produces
# the reliability diagram with no cloud or keys:
#   docker build -t calibrated-readiness .
#   docker run --rm -v "$PWD/data:/app/data" calibrated-readiness
#
# To also install the Microsoft Agent Framework layer (for the live Foundry demo):
#   docker build --build-arg INSTALL_AGENTS=true -t calibrated-readiness:agents .
# Note the version-matrix caveat in docs/LIVE_FOUNDRY_NOTES.md before a live run.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-agents.txt ./
RUN pip install --no-cache-dir -r requirements.txt

ARG INSTALL_AGENTS=false
RUN if [ "$INSTALL_AGENTS" = "true" ]; then \
        pip install --no-cache-dir -r requirements-agents.txt ; \
    fi

COPY . .
ENV PYTHONPATH=/app

# Default command: regenerate the falsifiable headline artifact.
CMD ["python", "scripts/run_calibration.py"]
