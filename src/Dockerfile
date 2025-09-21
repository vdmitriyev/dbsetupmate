FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
	dos2unix \
	iputils-ping \
	fonts-freefont-ttf \
	nano \
	tzdata \
	procps \
    git \
	build-essential

# create the app user
RUN addgroup --system app && adduser --system --group app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements requirements

RUN pip install uv
RUN uv pip install --system --no-cache-dir -r requirements/requirements.txt
RUN uv pip install --system --no-cache-dir -r requirements/requirements-pgsql.txt

COPY *.py ./
COPY *.sh ./
RUN dos2unix *.sh
RUN chmod +x *.sh

EXPOSE 8001

# test/debug mode
# CMD ["tail", "-f", "/dev/null"]