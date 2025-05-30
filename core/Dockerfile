# Build stage
FROM rust:1.75 as builder

WORKDIR /app

# Copy manifests
COPY Cargo.toml Cargo.lock ./

# Copy source code
COPY src ./src
COPY migrations ./migrations

# Build the application
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the binary from builder stage
COPY --from=builder /app/target/release/morphine-core /app/morphine-core

# Copy migrations
COPY --from=builder /app/migrations /app/migrations

# Create storage directory
RUN mkdir -p /app/storage/streams

# Expose port
EXPOSE 3001

# Run the binary
CMD ["./morphine-core"] 