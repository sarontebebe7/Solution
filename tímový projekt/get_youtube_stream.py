"""
Get direct stream URL from YouTube video/livestream
"""
import yt_dlp
import sys

def get_youtube_stream_url(youtube_url):
    """
    Extract direct stream URL from YouTube video/livestream
    
    Args:
        youtube_url: YouTube video or livestream URL
        
    Returns:
        Direct stream URL that can be used with OpenCV
    """
    ydl_opts = {
        'format': 'best[ext=mp4]',  # Get best quality MP4
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': ['default']}},  # Fix JS runtime warning
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
            # Get the direct URL
            if 'url' in info:
                stream_url = info['url']
            elif 'formats' in info:
                # Get best format
                formats = [f for f in info['formats'] if f.get('vcodec') != 'none']
                if formats:
                    stream_url = formats[-1]['url']
                else:
                    return None
            else:
                return None
            
            print(f"✅ Stream URL extracted successfully!")
            print(f"📺 Title: {info.get('title', 'Unknown')}")
            print(f"🔗 Direct URL: {stream_url}")
            print(f"\n💡 Use in config.yaml:")
            print(f'   camera:')
            print(f'     source: "{stream_url}"')
            
            return stream_url
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python get_youtube_stream.py <YouTube_URL>")
        print("Example: python get_youtube_stream.py https://www.youtube.com/watch?v=xxxxx")
        sys.exit(1)
    
    youtube_url = sys.argv[1]
    get_youtube_stream_url(youtube_url)
