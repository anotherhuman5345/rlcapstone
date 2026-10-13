FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
# Placeholder scans unless real ones were added to stimuli/real_scans/ before the build.
RUN python stimuli/generate_stimuli.py
ENV PORT=8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
