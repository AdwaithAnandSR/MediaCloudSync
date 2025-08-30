import os
import yt_dlp
import requests
import logging
from urllib.parse import urlparse, parse_qs
import tempfile
import re

class YouTubeProcessor:
    def __init__(self):
        self.external_api_base = "https://vivid-music.vercel.app"
        self.temp_dir = tempfile.gettempdir()
        
        # yt-dlp options for high-quality audio
        self.ydl_opts_audio = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
            'outtmpl': os.path.join(self.temp_dir, '%(id)s.%(ext)s'),
            'extractaudio': True,
            'audioformat': 'mp3',
            'audioquality': '0',  # Best quality (320kbps)
            'embed_subs': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
        }
        
        # yt-dlp options for thumbnails
        self.ydl_opts_thumbnail = {
            'skip_download': True,
            'writethumbnail': True,
            'outtmpl': os.path.join(self.temp_dir, '%(id)s.%(ext)s'),
            'ignoreerrors': True,
        }

    def extract_video_info(self, url):
        """Extract video information from a YouTube URL"""
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return None
                
                # Extract relevant information
                video_info = {
                    'id': info.get('id', ''),
                    'title': info.get('title', ''),
                    'duration': info.get('duration', 0),
                    'artist': info.get('uploader', '') or info.get('channel', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'url': url
                }
                
                logging.info(f"Extracted info for video: {video_info['title']}")
                return video_info
                
        except Exception as e:
            logging.error(f"Error extracting video info: {str(e)}")
            return None

    def extract_playlist_videos(self, url, skip=0, limit=10):
        """Extract videos from a playlist with pagination"""
        try:
            # Handle both playlist URLs and IDs
            if not url.startswith('http'):
                url = f"https://www.youtube.com/playlist?list={url}"
            
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info or 'entries' not in info:
                    return []
                
                entries = info['entries']
                
                # Apply pagination
                paginated_entries = entries[skip:skip + limit]
                
                videos = []
                for entry in paginated_entries:
                    if entry:
                        video_info = {
                            'id': entry.get('id', ''),
                            'title': entry.get('title', ''),
                            'duration': entry.get('duration', 0),
                            'artist': info.get('uploader', '') or info.get('channel', ''),
                            'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                        }
                        videos.append(video_info)
                
                logging.info(f"Extracted {len(videos)} videos from playlist")
                return videos
                
        except Exception as e:
            logging.error(f"Error extracting playlist videos: {str(e)}")
            return []

    def extract_channel_videos(self, url, skip=0, limit=10):
        """Extract videos from a channel with pagination"""
        try:
            # Handle different channel URL formats
            if url.startswith('@'):
                url = f"https://www.youtube.com/{url}"
            elif not url.startswith('http'):
                url = f"https://www.youtube.com/channel/{url}"
            
            # Add /videos to get the channel's videos
            if not url.endswith('/videos'):
                url = url.rstrip('/') + '/videos'
            
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info or 'entries' not in info:
                    return []
                
                entries = info['entries']
                
                # Apply pagination
                paginated_entries = entries[skip:skip + limit]
                
                videos = []
                for entry in paginated_entries:
                    if entry:
                        video_info = {
                            'id': entry.get('id', ''),
                            'title': entry.get('title', ''),
                            'duration': entry.get('duration', 0),
                            'artist': info.get('uploader', '') or info.get('channel', ''),
                            'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                        }
                        videos.append(video_info)
                
                logging.info(f"Extracted {len(videos)} videos from channel")
                return videos
                
        except Exception as e:
            logging.error(f"Error extracting channel videos: {str(e)}")
            return []

    def download_media(self, video_info):
        """Download audio and thumbnail for a video"""
        audio_path = None
        thumbnail_path = None
        
        try:
            # Download audio
            with yt_dlp.YoutubeDL(self.ydl_opts_audio) as ydl:
                ydl.download([video_info['url']])
                
                # Find the downloaded audio file
                for ext in ['mp3', 'webm', 'm4a', 'opus']:
                    potential_path = os.path.join(self.temp_dir, f"{video_info['id']}.{ext}")
                    if os.path.exists(potential_path):
                        audio_path = potential_path
                        break
            
            # Download thumbnail
            try:
                with yt_dlp.YoutubeDL(self.ydl_opts_thumbnail) as ydl:
                    ydl.download([video_info['url']])
                    
                    # Find the downloaded thumbnail
                    for ext in ['jpg', 'png', 'webp']:
                        potential_path = os.path.join(self.temp_dir, f"{video_info['id']}.{ext}")
                        if os.path.exists(potential_path):
                            thumbnail_path = potential_path
                            break
            except Exception as e:
                logging.warning(f"Could not download thumbnail: {str(e)}")
            
            logging.info(f"Downloaded media for: {video_info['title']}")
            return audio_path, thumbnail_path
            
        except Exception as e:
            logging.error(f"Error downloading media: {str(e)}")
            return None, None

    def check_song_exists(self, video_id, title):
        """Check if a song already exists using the external API"""
        try:
            response = requests.post(
                f"{self.external_api_base}/checkSongExistsByYtId",
                json={"id": video_id, "title": title},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('exists', False)
            else:
                logging.warning(f"External API returned status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Error checking if song exists: {str(e)}")
            return False

    def send_to_external_api(self, video_info, song_url, cover_url):
        """Send song details to the external API"""
        try:
            payload = {
                "title": video_info['title'],
                "songURL": song_url,
                "coverURL": cover_url,
                "id": video_info['id'],
                "artist": video_info['artist'],
                "duration": video_info['duration']
            }
            
            response = requests.post(
                f"{self.external_api_base}/addSong",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logging.info(f"Successfully sent song to external API: {video_info['title']}")
                return True
            else:
                logging.error(f"External API returned status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending to external API: {str(e)}")
            return False

    def cleanup_temp_files(self, *file_paths):
        """Clean up temporary files"""
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logging.debug(f"Cleaned up temp file: {file_path}")
                except Exception as e:
                    logging.warning(f"Could not remove temp file {file_path}: {str(e)}")
