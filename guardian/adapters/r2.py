from __future__ import annotations

import boto3


class R2ObjectStore:
    """Cloudflare R2 adapter using the S3-compatible API."""

    def __init__(
        self,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
    ) -> None:
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )

    def put_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"r2://{self.bucket}/{key}"

    def get_bytes(self, key: str) -> bytes:
        response = self.client.get_object(
            Bucket=self.bucket,
            Key=key,
        )
        return response["Body"].read()
