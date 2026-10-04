FROM python:3.11-slim

# Install ffmpeg for video processing.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy pyproject.toml and install dependencies.
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy source code.
COPY src ./src

# Create marker for py.typed (strict typing).
RUN touch src/moments/py.typed

# Default port.
EXPOSE 8000

# Run app.
CMD ["python", "-m", "moments"]
