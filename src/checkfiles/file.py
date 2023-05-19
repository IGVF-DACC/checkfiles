import gzip
import hashlib
import os

from typing import Optional


class File:
    def __init__(self, path: str, file_format: str):
        self.file_format = file_format
        self.path = path
        self.__size = os.path.getsize(path)
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
        self.validation_result = None

    def update_errors(self, error: dict):
        self.errors.update(error)

    def update_info(self, info: dict):
        self.info.update(info)
