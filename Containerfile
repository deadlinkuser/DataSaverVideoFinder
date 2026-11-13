FROM docker.io/library/python:3.12-slim
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt
COPY data_saver_video_finder.py /usr/local/bin/data_saver_video_finder.py
RUN chmod +x /usr/local/bin/data_saver_video_finder.py
WORKDIR /output
ENTRYPOINT ["python3", "-u", "/usr/local/bin/data_saver_video_finder.py"]
