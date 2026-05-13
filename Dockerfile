FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y sqlite3  && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Match prod: run as non-root so dev catches permission bugs prod would hit.
RUN useradd -m -u 1000 sabc && \
    mkdir -p /app/data /app/uploads/photos && \
    chown -R sabc:sabc /app
USER sabc

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
