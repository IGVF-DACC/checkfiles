import json
import logging
import traceback


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            'asctime': self.formatTime(record, self.datefmt),
            'levelname': record.levelname,
            'message': record.getMessage(),
        }
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = ''.join(
                    traceback.format_exception(*record.exc_info))
            if record.exc_text:
                data['exc_text'] = record.exc_text.splitlines()
        return json.dumps(data)
