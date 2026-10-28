import os
import sys
import subprocess
import boto3

BUCKET_NAME = os.getenv("S3_TEMP_BUCKET", "my-video-temp-storage")
s3_client = boto3.client("s3")

def run_command(command):
    """Run shell command and stream output."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    for line in process.stdout:
        print(line.decode("utf-8"), end="")
    process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"Command failed with code {process.returncode}: {command}")

def process_video(s3_input_key):
    local_input = "input_source.mp4"
    local_output = "output_final.mp4"

    print(f"📥 Downloading {s3_input_key} from S3...")
    s3_client.download_file(BUCKET_NAME, s3_input_key, local_input)

    # 1. Crop to Vertical Short (9:16 aspect ratio center crop)
    # Formula: crop=ih*9/16:ih:(in_w-ih*9/16)/2:0
    print("✂️ Cropping video to vertical 9:16 short...")
    cropped_file = "cropped.mp4"
    crop_cmd = f"ffmpeg -y -i {local_input} -vf \"crop=ih*9/16:ih:(in_w-ih*9/16)/2:0\" -c:a copy {cropped_file}"
    run_command(crop_cmd)

    # 2. Extract & Stitch Funny Scenes (Example clips: 00:00:10 to 00:00:20 and 00:00:45 to 00:00:55)
    print("🎬 Extracting and stitching funny moments...")
    
    # Clip 1
    run_command(f"ffmpeg -y -ss 00:00:10 -to 00:00:20 -i {cropped_file} -c copy clip1.mp4")
    # Clip 2
    run_command(f"ffmpeg -y -ss 00:00:45 -to 00:00:55 -i {cropped_file} -c copy clip2.mp4")

    # Create a concat list file for FFmpeg
    with open("concat_list.txt", "w") as f:
        f.write("file clip1.mp4\n")
        f.write("file clip2.mp4\n")

    # Stitch clips together
    run_command(f"ffmpeg -y -f concat -safe 0 -i concat_list.txt -c copy {local_output}")

    # 3. Upload Result Back to Temp Storage
    s3_output_key = "output/processed_short.mp4"
    print(f"📤 Uploading final video back to {s3_output_key}...")
    s3_client.upload_file(local_output, BUCKET_NAME, s3_output_key)
    print("✨ Processing pipeline completed successfully!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process.py <s3_input_key>")
        sys.exit(1)
    
    video_key = sys.argv[1]
    process_video(video_key)
