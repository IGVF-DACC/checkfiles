set -ex
goofys ${AWS_BUCKET_NAME} ${AWS_DATA_DIR}
python3 src/checkfiles/checkfiles.py
