FROM python:3.12-slim

RUN groupadd -r kegtracker && useradd -r -g kegtracker -d /app kegtracker

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY static/ static/

RUN mkdir -p /data && chown kegtracker:kegtracker /data

USER kegtracker

ENV DATABASE_URL=sqlite:////data/kegs.db
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
