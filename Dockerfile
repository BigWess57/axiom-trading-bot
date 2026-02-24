# Dockerfile for Solana trading bot
FROM python:3.11-slim

WORKDIR /app

# Install AxiomTradeAPI-py
RUN pip install --no-cache-dir axiomtradeapi

# Copy your trading bot code
COPY . .

# Run your trading bot
CMD ["python", "main.py"]