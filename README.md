# Checkfiles

An AWS Lambda function to check new or updated files in AWS S3 bucket to see if the size and MD5 sum (both for gzipped and ungzipped) are identical to the submitted metadata. It also checks some other properties for specific file type.

## External Dependencies

- [`requests`](https://pypi.org/project/phonenumbers/)

### How to install external dependencies?

- Creating a function deployment package by following the documentation [here](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html#python-package-dependencies).
- Creating a Lambda layer by following the documentation [here](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html#configuration-layers-path).

## Example Lambda Event

Amazon Connect sends the following payload to Lambda function inside a contact flow:

```json
{
  "Records": [
    {
      "eventVersion": "2.1",
      "eventSource": "aws:s3",
      "awsRegion": "us-west-2",
      "eventTime": "2022-10-31T15:56:55.840Z",
      "eventName": "ObjectCreated:Put",
      "userIdentity": {
        "principalId": "AWS:AIDAUXXXXXXXXXXXXXXXX"
      },
      "requestParameters": {
        "sourceIPAddress": "47.187.XXX.XX"
      },
      "responseElements": {
        "x-amz-request-id": "44Q5TEXXXXXXXXXX",
        "x-amz-id-2": "knwvflO5eS6qmj/o8o/ySiCTokuDQ2uMjQVtVVqx8b+iBrKaT6JNaocPGCiUQ8INFl6zXYZG7MjkXXXXXXXXXXXXXXXXXXXX"
      },
      "s3": {
        "s3SchemaVersion": "1.0",
        "configurationId": "d63ea988-1bcd-4d27-XXXX-XXXXXXXXXXXX",
        "bucket": {
          "name": "xxxxxxxxxxxx",
          "ownerIdentity": {
            "principalId": "A22RXXXXXXXXXX"
          },
          "arn": "arn:aws:s3:::xxxxxxxxxxxx"
        },
        "object": {
          "key": "2022/10/31/8b19341b-b1b2-4e10-ad7f-aa910ccd4d2c/ENCFF080HPN.tsv",
          "size": 1439779,
          "eTag": "e4aec322d041c6f987e17dbcf93a3465",
          "sequencer": "00635FF047BB6A870B"
        }
      }
    }
  ]
}
```

This can also be referenced [here](https://docs.aws.amazon.com/connect/latest/adminguide/connect-lambda-functions.html#function-contact-flow).

## Environment Variables

This Lambda function requires two environment variables:

- `USERNAME`: Access key ID for Encode database.
- `PASSWORD`: Secret access key for Encode database.

## File types for validation

- FASTQ
- BAM
- TXT
- TSV

## IAM Permissions

This Lambda function require at least a read access to the files stored in S3.

### Example

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject"
            ],
            "Resource": [
                "arn:aws:s3:::name-of-the-folder",
                "arn:aws:s3:::name-of-the-folder/*"
            ]
        }
    ]
}
```
