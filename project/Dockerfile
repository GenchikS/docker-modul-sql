FROM python:3.12-slim
WORKDIR /project
COPY . .
COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
CMD ["python3", "app.py"]