FROM python:3.7-slim

LABEL maintainer="Volker Kettenbach <volker@ktnbch.de>"

WORKDIR /srv

COPY requirements.txt ./

RUN apt update && apt upgrade -y
RUN apt install -y bash
RUN pip3 install --no-cache-dir --upgrade pip && pip3 install --no-cache-dir -r requirements.txt

RUN cp /usr/share/zoneinfo/Europe/Berlin /etc/localtime

COPY . .
# -u = unbuffered - otherwise there are no logs
CMD [ "python", "-u", "tellows.agi.py" ]
