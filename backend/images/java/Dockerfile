FROM eclipse-temurin:17-jdk-jammy

# Create non-root user (use UID 1001 to avoid conflicts)
RUN useradd -m -u 1001 -s /bin/bash sandboxuser

# Create working directory
RUN mkdir -p /code && chown sandboxuser:sandboxuser /code


# Set working directory
WORKDIR /code

# Switch to non-root user
USER sandboxuser
