FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CULTURE_PULSE_DATA=/app/DATASET \
    GEMINI_API_KEY=AQ.Ab8RN6K8-sg6eZ2ru31kJofFpAki3j3bjOZg_uIkZLigNfAHKw

RUN pip install --no-cache-dir \
    "fastapi>=0.115" \
    "uvicorn[standard]>=0.30" \
    "pandas>=2.2" \
    "numpy>=2.0" \
    "scikit-learn>=1.5" \
    "scipy>=1.13" \
    "pydantic>=2.7" \
    "openpyxl>=3.1.5" \
    "xlrd>=2.0.2"

COPY DATASET /app/DATASET
COPY backend/app /app/app

EXPOSE 8010

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
