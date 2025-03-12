import gzip
import hashlib
import json
import logging
import os

from typing import Optional


class File:
    def __init__(self, path: str, file_format: str):
        self.file_format = file_format
        self.path = path
        self.__size = None
        self.__md5sum = None
        self.__content_md5sum = None
        self.__is_zipped = None

    @property
    def md5sum(self):
        if self.__md5sum is not None:
            return self.__md5sum
        else:
            self.__md5sum = self._calculate_md5sum()
            return self.__md5sum

    @property
    def content_md5sum(self):
        if not self.is_zipped:
            raise TypeError('Content md5 only makes sense for gzipped files')
        elif self.__content_md5sum is not None:
            return self.__content_md5sum
        else:
            self.__content_md5sum = self._calculate_content_md5sum()
            return self.__content_md5sum

    @property
    def is_zipped(self):
        if self.__is_zipped is not None:
            return self.__is_zipped
        else:
            self.__is_zipped = self._is_zipped()
            return self.__is_zipped

    @property
    def size(self):
        if self.__size is not None:
            return self.__size
        else:
            self.__size = os.path.getsize(self.path)
            return self.__size

    def _calculate_content_md5sum(self):
        return self._calculate_md5sum(open_func=gzip.open)

    def _calculate_md5sum(self, chunk_size=4096, open_func=open):
        hash_md5 = hashlib.md5()
        with open_func(self.path, 'rb') as fp:
            while chunk := fp.read(chunk_size):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _is_zipped(self):
        try:
            gzip.GzipFile(filename=self.path).read(1)
            return True
        except gzip.BadGzipFile:
            return False


def get_file(path, file_format):
    return File(path, file_format)


class FileValidationRecord:
    def __init__(self, file: File, uuid: Optional[str] = None):
        self.file = file
        self.uuid = uuid
        self.errors = {}
        self.info = {}
        self.file_not_found = False
        self.validation_success = None
        self.__original_etag = None

    def update_errors(self, error: dict):
        self.errors.update(error)

    def update_info(self, info: dict):
        self.info.update(info)

    @property
    def content_md5sum(self):
        if self.uuid:
            logging.info(f'Getting content md5sum for uuid: {self.uuid}')
        try:
            content_md5sum = self.file.content_md5sum
        except Exception as e:
            logging.error(
                f'Error getting content md5sum for uuid: {self.uuid}')
            logging.error(e)
            raise e
        return content_md5sum

    @property
    def original_etag(self):
        return self.__original_etag

    @original_etag.setter
    def original_etag(self, value):
        if self.__original_etag is not None:
            raise ValueError('Cannot set original_etag twice.')
        self.__original_etag = value

    def make_payload(self):
        payload = {}
        if self.errors:
            payload.update(
                {'validation_error_detail': json.dumps(self.errors)})
            payload.update({'upload_status': 'invalidated'})
        if self.info:
            payload.update(self.info)
        if self.validation_success:
            payload.update({'upload_status': 'validated'})
        if self.file_not_found:
            payload.update({'upload_status': 'file not found'})
        return json.dumps(payload)
