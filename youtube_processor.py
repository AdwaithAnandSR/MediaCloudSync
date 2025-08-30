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
            ydl_opts = {'quiet': True}
            
            # Add cookies if available
            cookie_path = os.path.join(os.getcwd(), 'cookies.txt')
            if os.path.exists(cookie_path):
                if self._validate_cookie_format(cookie_path):
                    ydl_opts['cookiefile'] = cookie_path
                    logging.info("Using cookies.txt for authentication")
                else:
                    logging.warning("cookies.txt format invalid, proceeding without cookies")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
                
                logging.info(f"Extracted info for video: {video_info['title']} (Duration: {video_info['duration']}s)")
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
            # Add cookies to download options if available
            audio_opts = self.ydl_opts_audio.copy()
            thumbnail_opts = self.ydl_opts_thumbnail.copy()
            
            cookie_path = os.path.join(os.getcwd(), 'cookies.txt')
            if os.path.exists(cookie_path) and self._validate_cookie_format(cookie_path):
                audio_opts['cookiefile'] = cookie_path
                thumbnail_opts['cookiefile'] = cookie_path
            
            # Download audio
            with yt_dlp.YoutubeDL(audio_opts) as ydl:
                ydl.download([video_info['url']])
                
                # Find the downloaded audio file
                for ext in ['mp3', 'webm', 'm4a', 'opus']:
                    potential_path = os.path.join(self.temp_dir, f"{video_info['id']}.{ext}")
                    if os.path.exists(potential_path):
                        audio_path = potential_path
                        break
            
            # Download thumbnail
            try:
                with yt_dlp.YoutubeDL(thumbnail_opts) as ydl:
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

    def _validate_cookie_format(self, cookie_path):
        """Validate if cookies.txt is in Netscape format"""
        try:
            with open(cookie_path, 'r') as f:
                lines = f.readlines()
            
            # Check for Netscape format header
            if not lines:
                return False
            
            # Look for the Netscape header or valid cookie entries
            has_netscape_header = any('Netscape HTTP Cookie File' in line for line in lines[:5])
            has_valid_cookies = False
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('\t')
                    if len(parts) >= 6:  # Valid Netscape cookie format has at least 6 tab-separated fields
                        has_valid_cookies = True
                        break
            
            if has_netscape_header or has_valid_cookies:
                return True
            
            # Try to convert if it's not in proper format
            return self._try_convert_cookie_format(cookie_path)
            
        except Exception as e:
            logging.error(f"Error validating cookie format: {str(e)}")
            return False

    def _try_convert_cookie_format(self, cookie_path):
        """Try to convert cookies to Netscape format"""
        try:
            # This is a basic conversion attempt - in practice, you might need
            # more sophisticated parsing depending on the input format
            logging.warning("Attempting to convert cookies to Netscape format")
            
            backup_path = cookie_path + '.backup'
            os.rename(cookie_path, backup_path)
            
            with open(backup_path, 'r') as f:
                content = f.read()
            
            # If it looks like JSON (common export format)
            if content.strip().startswith('[') or content.strip().startswith('{'):
                logging.error("JSON cookie format detected - automatic conversion not supported")
                os.rename(backup_path, cookie_path)  # Restore original
                return False
            
            # Restore original file if conversion fails
            os.rename(backup_path, cookie_path)
            logging.warning("Could not convert cookie format automatically")
            return False
            
        except Exception as e:
            logging.error(f"Error converting cookie format: {str(e)}")
            return False

    def is_duration_valid(self, duration):
        """Check if video duration is between 2 and 8 minutes"""
        if not duration:
            return False
        return 120 <= duration <= 480  # 2 minutes to 8 minutes in seconds
