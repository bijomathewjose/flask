import boto3
from botocore.exceptions import NoCredentialsError,PartialCredentialsError,ClientError,EndpointConnectionError,BotoCoreError
import mimetypes
import os
from app import logger
BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
s3_client = None

def setup_s3_client():
    """
    Initializes and returns a boto3 S3 client with proper error handling.

    Returns:
        boto3.client: An initialized S3 client.

    Raises:
        S3ClientError: If there's an issue setting up the S3 client.
    """
    global s3_client
    if s3_client:
        return s3_client

    try:
        # Attempt to create the S3 client
        s3_client = boto3.client('s3')
        return s3_client

    except NoCredentialsError:
        raise Exception("AWS credentials not available.")

    except PartialCredentialsError:
        raise Exception("Incomplete AWS credentials provided.")

    except EndpointConnectionError:
        raise Exception("Unable to connect to the AWS endpoint. Check your network connection and AWS region.")

    except ClientError as e:
        # Handle client-related errors (e.g., invalid permissions)
        raise Exception(f"AWS ClientError: {e}") from e

    except BotoCoreError as e:
        # Handle other Boto3 core errors
        raise Exception(f"BotoCoreError: {e}") from e

    except Exception as e:
        # Catch-all for any other exceptions
        raise Exception(f"Unexpected error setting up S3 client: {e}") from e


def upload_to_s3(file_content, file_name, bucket_name=BUCKET_NAME,directory_name=None, content_type=None):
    try:
        logger.info(f"Uploading to S3: {file_name}")
        client = setup_s3_client()

        if directory_name:
            file_name = f"{directory_name}/{file_name}"
        logger.info(f"File name: {file_name}")
        # Determine content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(file_name)
            if not content_type:
                content_type = 'application/octet-stream'
        logger.info(f"Content type: {content_type}")
        client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=file_content,
            ContentType=content_type
        )
        logger.info(f"Uploaded to S3: {file_name}")
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{file_name}"
        logger.info(f"S3 URL: {s3_url}")
        return s3_url

    except NoCredentialsError:
        raise Exception("AWS credentials not available")
    except Exception as e:
        raise Exception(f"Error uploading to S3: {str(e)}")
