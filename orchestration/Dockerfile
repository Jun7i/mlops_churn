FROM apache/airflow:2.7.3-python3.10

USER root

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    apache-airflow-providers-postgres \
    apache-airflow-providers-docker \
    psycopg2-binary \
    pandas==2.1.4 \
    numpy==1.26.2 \
    scikit-learn==1.3.2 \
    xgboost==2.0.3 \
    imbalanced-learn==0.11.0 \
    mlflow==2.16.2 \
    sqlalchemy>=2.0.0 \
    matplotlib==3.8.2 \
    seaborn==0.13.1 \
    fastapi==0.109.0 \
    pydantic==2.5.3 \
    python-dotenv==1.0.0 \
    joblib==1.3.2 \
    pyarrow==14.0.2 \
    dbt-core==1.7.4 \
    dbt-postgres==1.7.4

# Set Airflow home
ENV AIRFLOW_HOME=/opt/airflow

# Expose Airflow webserver port
EXPOSE 8080
