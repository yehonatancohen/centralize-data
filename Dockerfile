FROM python:3.10-slim

# Create a non-root user (required by HF Spaces)
RUN useradd -m -u 1000 user

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create writable directories for data and uploads
RUN mkdir -p /app/data /app/uploads /app/app/static && \
    chown -R user:user /app

USER user

EXPOSE 7860

CMD ["python", "run.py"]
