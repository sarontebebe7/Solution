"""
Download sample video for testing
This downloads a short video with people for testing the detection system
"""

import requests
import os

def download_sample_video():
    """Download a sample video with people"""
    
    # Sample videos with people (small size, public domain)
    videos = [
        {
            "name": "sample_people_walking.mp4",
            "url": "https://sample-videos.com/video321/mp4/240/big_buck_bunny_240p_1mb.mp4",
            "description": "Sample animation (Big Buck Bunny)"
        },
        {
            "name": "pexels_people.mp4", 
            "url": "https://cdn.pixabay.com/video/2016/06/24/3788-170598284_tiny.mp4",
            "description": "Real people walking (Pixabay)"
        }
    ]
    
    print("=" * 60)
    print("Sample Video Downloader for Testing")
    print("=" * 60)
    print()
    
    print("Available videos:")
    for i, video in enumerate(videos, 1):
        print(f"{i}. {video['description']}")
        print(f"   File: {video['name']}")
        print()
    
    choice = input("Select video to download (1-2, or 'all'): ").strip()
    
    if choice.lower() == 'all':
        to_download = videos
    else:
        try:
            idx = int(choice) - 1
            to_download = [videos[idx]]
        except:
            print("Invalid choice!")
            return
    
    for video in to_download:
        print(f"\nDownloading {video['name']}...")
        try:
            response = requests.get(video['url'], stream=True, timeout=30)
            response.raise_for_status()
            
            with open(video['name'], 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✓ Downloaded: {video['name']}")
            print(f"  Update config.yaml with: source: \"{video['name']}\"")
            
        except Exception as e:
            print(f"✗ Failed to download {video['name']}: {e}")
    
    print("\n" + "=" * 60)
    print("Download complete!")
    print("\nTo use the video:")
    print("1. Edit config.yaml")
    print("2. Change camera.source to the video filename")
    print("3. Restart the server: python main.py")
    print("=" * 60)

if __name__ == "__main__":
    download_sample_video()
