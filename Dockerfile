FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DATABASE_URL=postgresql://user:password@postgres/dbname
ENV SECRET_KEY=your_secret_key_here
ENV ALGORITHM=HS256
ENV ACCESS_TOKEN_EXPIRE_MINUTES=30

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--reload"]