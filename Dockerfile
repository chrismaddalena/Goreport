FROM python:3
ADD . /
RUN pip install -r requirements.txt
ENTRYPOINT [ "python", "./GoReport.py" ]
