FROM python:3.12-slim

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


RUN apt-get update && apt-get install -y \
    build-essential \
    libopencv-dev \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*


RUN pip install --upgrade pip

RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu



COPY requirements.txt /usr/src/app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# RUN useradd -ms /bin/bash celeryuser

COPY . /usr/src/app

EXPOSE 5000

# USER celeryuser

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout",  "120", "app:app"]
