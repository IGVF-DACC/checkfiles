
set -ex
# just in case ...
# sudo chown -R ${UID}:${UID} ${DATA_DIR}

# run with given user
gcsfuse --key-file=${GOOGLE_APPLICATION_CREDENTIALS} ${BUCKET_NAME} ${DATA_DIR}
echo foobarbaz
ls /mnt
python3 checkfiles/checkfiles.py
