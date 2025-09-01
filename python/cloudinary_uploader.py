import os
import cloudinary
import cloudinary.uploader
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CloudinaryUploader:
    def __init__(self):
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
            api_key=os.getenv('CLOUDINARY_API_KEY'),
            api_secret=os.getenv('CLOUDINARY_API_SECRET')
        )

                    
        # Verify configuration
        if not all([
            os.getenv('CLOUDINARY_CLOUD_NAME'),
            os.getenv('CLOUDINARY_API_KEY'),
            os.getenv('CLOUDINARY_API_SECRET')
        ]):
            logging.error("Cloudinary credentials not properly configured")
            raise ValueError("Cloudinary credentials missing in environment variables")

       


    def upload_media(self, audio_path, thumbnail_path, video_info):
        """Upload audio and thumbnail to Cloudinary with immediate cleanup"""
        song_url = None
        cover_url = None
        
        try:
            # Upload audio file and clean up immediately
            if audio_path and os.path.exists(audio_path):
                try:
                    audio_result = cloudinary.uploader.upload(
                        audio_path,
                        resource_type="video",  # Use video resource type for audio
                        public_id=f"songs/{video_info['id']}",
                        tags=["youtube", "song"],
                        context={
                            "title": video_info['title'],
                            "artist": video_info['artist'],
                            "duration": str(video_info['duration'])
                        }
                    )
                    song_url = audio_result.get('secure_url')
                    logging.info(f"Uploaded audio to Cloudinary: {song_url}")
                finally:
                    # Clean up audio file immediately after upload attempt
                    self._cleanup_files(audio_path)
            
            # Upload thumbnail and clean up immediately
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    thumbnail_result = cloudinary.uploader.upload(
                        thumbnail_path,
                        resource_type="image",
                        public_id=f"covers/{video_info['id']}",
                        tags=["youtube", "cover"],
                        context={
                            "title": video_info['title'],
                            "artist": video_info['artist']
                        }
                    )
                    cover_url = thumbnail_result.get('secure_url')
                    logging.info(f"Uploaded cover to Cloudinary: {cover_url}")
                finally:
                    # Clean up thumbnail file immediately after upload attempt
                    self._cleanup_files(thumbnail_path)
            
            return song_url, cover_url
            
        except Exception as e:
            logging.error(f"Error uploading to Cloudinary: {str(e)}")
            # Final cleanup in case of any remaining files
            self._cleanup_files(audio_path, thumbnail_path)
            return None, None

    def _cleanup_files(self, *file_paths):
        """Clean up local files"""
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logging.debug(f"Cleaned up file: {file_path}")
                except Exception as e:
                    logging.warning(f"Could not remove file {file_path}: {str(e)}")

    def delete_media(self, public_id, resource_type="video"):
        """Delete media from Cloudinary"""
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            logging.info(f"Deleted from Cloudinary: {public_id}")
            return result
        except Exception as e:
            logging.error(f"Error deleting from Cloudinary: {str(e)}")
            return None

    def get_media_info(self, public_id, resource_type="video"):
        """Get media information from Cloudinary"""
        try:
            result = cloudinary.api.resource(public_id, resource_type=resource_type)
            return result
        except Exception as e:
            logging.error(f"Error getting media info from Cloudinary: {str(e)}")
            return None
