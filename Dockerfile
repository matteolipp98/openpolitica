# Immagine dei worker Python (Render, servizio Docker sul branch main). Il sito è su Vercel.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

WORKDIR /app
# Dipendenze prima del codice, per sfruttare la cache degli strati
COPY workers/pyproject.toml workers/uv.lock workers/
RUN cd workers && uv sync --frozen --no-dev --no-install-project

COPY workers/ workers/
COPY content/ content/
COPY supabase/ supabase/
RUN cd workers && uv sync --frozen --no-dev

RUN useradd --create-home op && chown -R op /app
USER op

WORKDIR /app/workers
EXPOSE 10000
CMD ["uv", "run", "--no-sync", "python", "-m", "op_workers.servizio"]
