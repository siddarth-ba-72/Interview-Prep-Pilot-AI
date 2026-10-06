# ai-service for the load-test stack. Same as ai-service/Dockerfile; the difference is the
# ignore file next to this one, which keeps ai-service/.env (the real OpenAI key) out of the image.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
