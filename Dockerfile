FROM --platform=linux/amd64 registry.dp.tech/mlops/mirrors/continuumio/miniconda3:4.12.0

ADD sources.list /etc/apt/sources.list
RUN apt-get update 
RUN apt-get install gcc python3-dev libgl1-mesa-glx xvfb  -y

RUN mkdir -p /app
ADD requirements.txt /app/requirements.txt

# Install dependencies
RUN pip3 install -r /app/requirements.txt -i https://repo.mlops.dp.tech/repository/pypi-group/simple

ADD assets/ /app/assets
ENTRYPOINT [ "gunicorn", "--bind", "0.0.0.0:50002", "-w", "4", "-t", "300", "--preload", "--chdir", "/app", "app:server" ]

ADD app.py /app/app.py
