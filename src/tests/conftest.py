import pytest


@pytest.fixture
def event_new_file():
    return {
        'Records': [
            {
                'messageId': '5ba51b39-01ed-4f71-adb5-ec059cfca0ca',
                'receiptHandle': 'AQEBpG1/Dn4g+I2IT9NF0wG2/3OH4zAJwMTRSyK5qkOnvVE/Zs5oztHJVeeQ8wxkj+d4Ed03mOwq7UIN+JtrcP2O0FRMzOnwUwuUpE965+qc8sge539Sy0JepHHUKek5eNrJSYtHHtd5t6EOlsfnjARkyPd9ttoDxUlr+biNMA4sD26MKTLrwyp2zt0zFJZUSKjFuS/huxS2PGTnxUDilSRwQv39XVQW2RuKNOBhjAjh2UXytYr+EdV3Z2mtoZwoUDTzXZPrOCuNenlsE+qMFEpJJH0IFHfj+hYlksyQWZRXboH9ZJeeWh0YMarEESDMcURM9qFUSILK0NmJUzahEu9/aCowU73Gi5kg8ykN2eQ42cZ//PQ/3vwOhatmmDtYyH53CDNeoNe2nOt5DKAr4xMljQ==',
                'body': "{\"Records\":[{\"eventVersion\":\"2.1\",\"eventSource\":\"aws:s3\",\"awsRegion\":\"us-west-2\",\"eventTime\":\"2022-11-03T14:26:47.419Z\",\"eventName\":\"ObjectCreated:Put\",\"userIdentity\":{\"principalId\":\"AWS:AIDAUDFZCSGXF3KECAQ3H\"},\"requestParameters\":{\"sourceIPAddress\":\"47.187.164.58\"},\"responseElements\":{\"x-amz-request-id\":\"CADXBZP0EMF1P0EN\",\"x-amz-id-2\":\"2Y0LNUrBO4ofXiBEIvUivTiCQgB+SiaPc6WDU3zBv3RymUILpm/iuaW1KnhVv+l5tM+FOZjqKnP/XW2xhYJhbm9PAMLonjkZ\"},\"s3\":{\"s3SchemaVersion\":\"1.0\",\"configurationId\":\"sqs-trigger\",\"bucket\":{\"name\":\"checkfile-mingjie\",\"ownerIdentity\":{\"principalId\":\"A22RVPTF9VSGSX\"},\"arn\":\"arn:aws:s3:::checkfile-mingjie\"},\"object\":{\"key\":\"2022/10/31/8b19341b-b1b2-4e10-ad7f-aa910ccd4d2c/ENCFF080HPN.tsv\",\"size\":1439779,\"eTag\":\"e4aec322d041c6f987e17dbcf93a3465\",\"sequencer\":\"006363CFA7501D5998\"}}}]}",
                'attributes': {
                    'ApproximateReceiveCount': '1',
                    'SentTimestamp': '1667485608151',
                    'SenderId': 'AIDAJFWZWTE5KRAMGW5A2',
                    'ApproximateFirstReceiveTimestamp': '1667485608162'
                },
                'messageAttributes': {},
                'md5OfBody': '5ed12fada8ba77fac8601ab906f4d91e',
                'eventSource': 'aws:sqs',
                'eventSourceARN': 'arn:aws:sqs:us-west-2:281708499374:CheckfilesQueue',
                'awsRegion': 'us-west-2'
            }
        ]
    }


@pytest.fixture
def event_new_folder():
    return {
        'Records': [
            {
                'messageId': '73c3e03e-7d70-4620-980d-54ea075b79f0',
                'receiptHandle': 'AQEBToB9PJdcFMV5F6MkSlmdFBuIIVJPLKc7mJghQnypaEzBt+GFaHAhCIM+s5Ebr4iJCpWtCxSZoWVWRMPBjNMEmTHLAHjtsHEX+l0cOsV10YHGWSRsPT26F6yCOQI4P+EGmOAlF7QV9ef0OzwwEnr3Xg2wSlxv6UhYKRYK/IRT7M6PauTmE+Ewc0JlJXaj4HRJRSXhsedLcOBnE/fgYBKAzsvsOFdqaPcPtgBS9TqZOMMs/zU6Q83rFJtGT74RJaD+NeoagKvR2gC5tHfyP82FhC3k7PaDlQjVh8nw/siiz7u2QzlyqC7oov1AVYTmPJafpmtOeVUIbliYzVi7pqXbDGjtZZsMg9khYWpOMvRqYkRc5CDqwLaMrbcYY3XPoyEXYUZWFeTr25+CCNr9vhEwEA==',
                'body': "{\"Records\":[{\"eventVersion\":\"2.1\",\"eventSource\":\"aws:s3\",\"awsRegion\":\"us-west-2\",\"eventTime\":\"2022-11-03T14:35:29.013Z\",\"eventName\":\"ObjectCreated:Put\",\"userIdentity\":{\"principalId\":\"AWS:AIDAUDFZCSGXF3KECAQ3H\"},\"requestParameters\":{\"sourceIPAddress\":\"47.187.164.58\"},\"responseElements\":{\"x-amz-request-id\":\"HFZBHRSWHZT6FCF7\",\"x-amz-id-2\":\"Z5CWplBQHlW+KGAWcxmhb2ksX7hGDMLSLa5ir/nRMJOm9+IFyNLCTsOY2ILMKPzg1nsIycmVu4jIJPo76mXK9t3NC6DwD4JM\"},\"s3\":{\"s3SchemaVersion\":\"1.0\",\"configurationId\":\"sqs-trigger\",\"bucket\":{\"name\":\"checkfile-mingjie\",\"ownerIdentity\":{\"principalId\":\"A22RVPTF9VSGSX\"},\"arn\":\"arn:aws:s3:::checkfile-mingjie\"},\"object\":{\"key\":\"2022/11/\",\"size\":0,\"eTag\":\"d41d8cd98f00b204e9800998ecf8427e\",\"sequencer\":\"006363D1B0F7B494F1\"}}}]}",
                'attributes': {
                    'ApproximateReceiveCount': '1',
                    'SentTimestamp': '1667486130263',
                    'SenderId': 'AIDAJFWZWTE5KRAMGW5A2',
                    'ApproximateFirstReceiveTimestamp': '1667486130272'
                },
                'messageAttributes': {},
                'md5OfBody': '5a7694bfaaf01702cc9b6a4f03781996',
                'eventSource': 'aws:sqs',
                'eventSourceARN': 'arn:aws:sqs:us-west-2:281708499374:CheckfilesQueue',
                'awsRegion': 'us-west-2'
            }
        ]
    }
