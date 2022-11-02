from checkfiles.lambda_function import lambda_handler


def test_lambda_handler_folder(event_new_folder):
    return_data = lambda_handler(event_new_folder, '')
    assert return_data == None
