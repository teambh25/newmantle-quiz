FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel
WORKDIR /src
COPY requirements.txt ./
RUN pip install -r requirements.txt
# ENTRYPOINT ["python", "main.py"]