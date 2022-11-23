FROM python:3.11.0

WORKDIR /checkfiles

# Install and upgrade pip
RUN pip install --upgrade pip

# Collect pip requirements
COPY requirements.txt .

# Install pip requirements
RUN pip install -r requirements.txt

COPY key.json .

ENV GOOGLE_APPLICATION_CREDENTIALS key.json

COPY src/ .


CMD ["python", "checkfiles/checkfiles.py"]
