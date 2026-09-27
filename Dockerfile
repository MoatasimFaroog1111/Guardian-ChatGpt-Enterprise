FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY guardian ./guardian
RUN pip install --no-cache-dir .
ENV GUARDIAN_DB=/data/guardian.db
RUN mkdir -p /data
EXPOSE 8000
CMD ["uvicorn","guardian.api.app:app","--host","0.0.0.0","--port","8000"]
