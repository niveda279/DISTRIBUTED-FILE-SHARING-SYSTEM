FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run node1 (override with env)
CMD ["sh", "-c", "cd node${NODE_NUM:-1} && python run.py"]
