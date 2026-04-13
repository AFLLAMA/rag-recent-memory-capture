# Use a specialized uv image for faster dependency management
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

# Set the working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project files for dependency installation first (leveraging Docker cache)
COPY pyproject.toml uv.lock ./

# Install dependencies without the project itself
RUN uv sync --frozen --no-install-project

# Copy the rest of the application
COPY . .

# Install the project
RUN uv sync --frozen

# Final Stage
FROM python:3.14-slim-bookworm

WORKDIR /app

# Copy the virtual environment and app from the builder
COPY --from=builder /app /app

# Add the virtual environment's bin to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Default command: show help (can be overridden in docker-compose)
CMD ["de-assist", "--help"]
