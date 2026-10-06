FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fake_llm ./fake_llm
EXPOSE 8090
# One worker keeps /stats and PATCH /admin/config consistent. With uvloop it holds several
# hundred concurrent streams; raise FAKE_LLM_STREAM_TICK_MS if it ever becomes the bottleneck.
CMD ["uvicorn", "fake_llm.main:app", "--host", "0.0.0.0", "--port", "8090", "--no-access-log", "--timeout-keep-alive", "75"]
