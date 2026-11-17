FROM python:3.14-slim

# what the image is, for registries and tools like Watchtower - a release
# build adds its version, source and commit too (docker/metadata-action),
# and repeats these, which must stay the same (.github/workflows/docker.yml)
LABEL org.opencontainers.image.title="Soloblog" \
      org.opencontainers.image.description="A blog and personal website for one person, that you run yourself" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="ZRPlus Studio" \
      org.opencontainers.image.url="https://github.com/soloblog/soloblog" \
      org.opencontainers.image.source="https://github.com/soloblog/soloblog" \
      org.opencontainers.image.documentation="https://github.com/soloblog/soloblog/blob/master/docs/DEPLOYMENT.md"

WORKDIR /app

# unbuffered so the first-run setup token (printed at startup) shows up
# in your host's log viewer straight away, not stuck in a buffer
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# fewer memory pools, one per thread otherwise: making smaller copies of
# 80 pictures at once peaked at 108 MB with it, 238 MB without
ENV MALLOC_ARENA_MAX=2

# libjpeg/libwebp for Pillow's jpeg/webp support
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo libwebp7 \
    && rm -rf /var/lib/apt/lists/*

# the user Soloblog runs as - app.py starts as root, hands it /data and
# switches (python app.py), so a host's root-owned disk keeps working
RUN useradd --system --uid 10001 --home-dir /app --no-create-home soloblog

COPY requirements.txt .
# pip isn't needed once the packages are in, and its bundled copies of
# other packages make image scanners (Trivy) report holes the app never
# uses. An update is a new image, built with pip and then without it.
RUN pip install -r requirements.txt \
    && pip uninstall -y pip \
    && rm -rf /usr/local/lib/python3.*/ensurepip

COPY . .

# daisyft compiles static/css/input.css into output.css - the one
# stylesheet the app serves - with the Tailwind + daisyUI program
# (tailwind-cli-extra). Runs after COPY because Tailwind scans the Python
# source for the class names it needs to generate.
# The program is one pinned version, checked against the checksum GitHub
# publishes for it, and fetched from the release itself: `daisyft init`
# asked GitHub's API for the latest on every build, which ran into its
# hourly limit (a failed release build) and could change the stylesheet
# under a release without anyone choosing to. To update: a newer tag from
# github.com/dobicinaitis/tailwind-cli-extra/releases and its two
# linux-x64 / linux-arm64 sha256 digests (docs/MAINTAINING.md).
ARG TAILWIND_EXTRA=v2.10.31
ARG TARGETARCH
RUN set -e; \
    case "$TARGETARCH" in \
      arm64) arch=arm64; sum=0d3c4830e87f8e0c17c8d70190c13055f19181c8ca29cc6520ae1ff7eb2947e2 ;; \
      *) arch=x64; sum=aca04df159cc3b2c4a984c58ddb066ca892ac5fda21755207ff08ac081cb9854 ;; \
    esac; \
    bin=".daisyft/bin/tailwindcss-linux-$arch"; \
    mkdir -p .daisyft/bin; \
    python -c "import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])" \
        "https://github.com/dobicinaitis/tailwind-cli-extra/releases/download/$TAILWIND_EXTRA/tailwindcss-extra-linux-$arch" \
        "$bin"; \
    echo "$sum  $bin" | sha256sum -c -; \
    chmod +x "$bin"; \
    PYTHONUTF8=1 daisyft build --minify; \
    rm -rf .daisyft/bin

ENV ENV=production \
    DATA_DIR=/data \
    PORT=8080
EXPOSE 8080

# no VOLUME instruction on purpose - some hosts (Railway) reject it.
# Mount persistent storage at /data yourself: see docs/DEPLOYMENT.md.

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8080\")}/healthz', timeout=4)"

CMD ["python", "app.py"]
