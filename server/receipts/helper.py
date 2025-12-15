from google.cloud import storage
from datetime import timedelta
from django.conf import settings

def generate_signed_upload_url(object_name, content_type):
    client = storage.Client()
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(object_name)

    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=60),
        method="PUT",
        content_type=content_type,
    )


def generate_signed_download_url(object_name):
    client = storage.Client()
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(object_name)

    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=60),
        method="GET",
    )

def generate_signed_view_url(bucket_name: str, blob_name: str):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=60),  # ⏱ 60 minutes
        method="GET",
    )

    return url
