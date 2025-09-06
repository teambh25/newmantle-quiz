FROM python:slim
WORKDIR /src
COPY requirements.txt ./
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "main.py"]
CMD ["--date", "YYYY-MM-DD"]