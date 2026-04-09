FROM python:3.10-slim

# Create a non-root user for security
RUN useradd -m chimera_user

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set ownership to non-root user
RUN chown -R chimera_user:chimera_user /app

# Switch to non-root user
USER chimera_user

# Expose port
EXPOSE 8000

# Run the trap listener
CMD ["python", "chimera_listener.py"]
