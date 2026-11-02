# CHECKFILES STEP FUNCTION DEPLOYMENT

If you are not sure this is what you should be running, you should not be running it.


## Installation

Install cdk 2.1031.2:

```bash
$ npm install -g aws-cdk@2.1031.2
```

Create python 3.11 virtual environment, and install packages:

```bash
$ python -m venv venv
$ echo "pip==26.2.2 --hash=sha256:fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70" > /tmp/pip-bootstrap.txt
$ python -m pip install --require-hashes -r /tmp/pip-bootstrap.txt
$ pip install -r requirements.txt -r requirements-dev.txt
```

Deploy sandbox stack:

```bash
$ cdk deploy RunCheckfilesStepFunctionSandbox --profile igvf-staging
```

Deploy production stack:

```bash
$ cdk deploy RunCheckfilesStepFunctionProduction --profile igvf-prod
```
