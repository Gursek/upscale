import os
import sys

import requests
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "product-images")

    if not supabase_url or not service_key:
        print("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required", file=sys.stderr)
        return 1

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    bucket_url = f"{supabase_url}/storage/v1/bucket/{bucket}"
    response = requests.get(bucket_url, headers=headers, timeout=30)

    if response.status_code == 200:
        print(f"Supabase Storage bucket already exists: {bucket}")
        return 0

    if response.status_code != 404:
        print(f"Could not check bucket: {response.status_code} {response.text}", file=sys.stderr)
        return 1

    create_response = requests.post(
        f"{supabase_url}/storage/v1/bucket",
        headers=headers,
        json={
            "id": bucket,
            "name": bucket,
            "public": True,
            "file_size_limit": 5 * 1024 * 1024,
            "allowed_mime_types": ["image/png", "image/jpeg", "image/webp"],
        },
        timeout=30,
    )

    if create_response.status_code not in (200, 201):
        print(
            f"Could not create bucket: {create_response.status_code} {create_response.text}",
            file=sys.stderr,
        )
        return 1

    print(f"Created Supabase Storage bucket: {bucket}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
