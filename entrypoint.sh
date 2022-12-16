set -ex
goofys ${AWS_BUCKET_NAME} ${AWS_DATA_DIR}
ls ${AWS_DATA_DIR}
goofys --endpoint https://storage.googleapis.com ${GOOGLE_BUCKET_NAME} ${GOOGLE_DATA_DIR}
ls ${GOOGLE_DATA_DIR}
