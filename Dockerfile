FROM python:3.12-slim
EXPOSE 8000

COPY . /occameracontrol
WORKDIR /occameracontrol

RUN pip install --no-cache-dir -r /occameracontrol/requirements.txt

USER nobody
ENTRYPOINT [ "python",  "-m", "occameracontrol"]
