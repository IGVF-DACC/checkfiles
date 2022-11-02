import pytest

@pytest.fixture
def event_new_file():
    return {
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
                "name": "name-of-the-bucket",
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

@pytest.fixture
def event_new_folder():
    return {
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
                        "name": "name-of-the-bucket",
                        "ownerIdentity": {
                            "principalId": "A22RXXXXXXXXXX"
                        },
                        "arn": "arn:aws:s3:::xxxxxxxxxxxx"
                    },
                    "object": {
                        "key": "2022/",
                        "size": 0,
                        "eTag": "d41d8cd98f00b204e9800998ecf8427e",
                        "sequencer": "00635FEEDFAA8E01A3"
                    }
                }
            }
        ]
    }