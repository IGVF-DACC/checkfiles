
set -ex
gcsfuse --key-file=${GOOGLE_APPLICATION_CREDENTIALS} ${BUCKET_NAME} ${DATA_DIR}
python3 checkfiles/checkfiles.py
