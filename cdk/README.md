# CHECKFILES STEP FUNCTION DEPLOYMENT

If you are not sure this is what you should be running, you should not be running it.


## Installation

Install cdk 2.88.0:

```bash
$ npm install aws-cdk@2.88.0
```

Create python 3.11 virtual environment, and install packages:

```bash
$ python -m venv venv
$ pip install -r requirements.txt -r requirements-dev.txt
```

Deploy lattice stack:

```bash
$ cdk deploy RunCheckfilesStepFunctionSandbox --profile lattice-prod
```
