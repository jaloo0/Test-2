import os
import streamlit as st
import boto3
import requests

# Configuration (Use environment variables or Streamlit secrets)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("S3_TEMP_BUCKET", "my-video-temp-storage")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "your-username/your-repo")

s3_client = boto3.client("s3", region_name=AWS_REGION)

st.set_page_config(page_title="Video Pipeline Dashboard", page_icon="🎬", layout="centered")

st.title("🎬 Video Short & Stitch Pipeline")
st.markdown("Upload a source video to temp storage, trigger cloud processing, and download your processed shorts.")

# --- Step 1: Upload Source Video ---
st.subheader("1. Upload Source Video")
uploaded_file = st.file_uploader("Choose a video file (MP4, MOV)", type=["mp4", "mov", "avi"])

if uploaded_file is not None:
    file_name = uploaded_file.name
    s3_key = f"incoming/{file_name}"

    if st.button("Upload & Trigger Pipeline"):
        with st.spinner("Uploading video to temp storage..."):
            try:
                # Upload to S3 Temp Storage
                s3_client.upload_fileobj(uploaded_file, BUCKET_NAME, s3_key)
                st.success(f"Uploaded successfully to `{s3_key}`!")
            except Exception as e:
                st.error(f"Upload failed: {e}")
                st.stop()

        with st.spinner("Triggering GitHub Actions workflow..."):
            # Trigger GitHub Actions workflow via Repository Dispatch API
            url = f"https://api.github.com/repos/{GITHUB_REPO}/dispatches"
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            }
            payload = {
                "event_type": "process_video",
                "client_payload": {"video_key": s3_key}
            }
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 204:
                st.success("Pipeline triggered successfully! Your video is being processed in the cloud.")
            else:
                st.error(f"Failed to trigger workflow: {response.text}")

st.divider()

# --- Step 2: Download Processed Video ---
st.subheader("2. Download Processed Results")
output_key = st.text_input("Processed File Key in Temp Storage", value="output/processed_short.mp4")

if st.button("Check & Download Result"):
    with st.spinner("Checking temp storage..."):
        try:
            # Generate a presigned URL for secure download
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': output_key},
                ExpiresIn=3600
            )
            st.success("Video ready for download!")
            st.video(presigned_url)
            st.markdown(f"[📥 Download Processed Video]({presigned_url})")
        except Exception as e:
            st.error(f"File not found or not ready yet: {e}")
