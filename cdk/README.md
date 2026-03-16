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
