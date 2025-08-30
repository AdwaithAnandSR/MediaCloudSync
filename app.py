import os
import logging
from flask import Flask, request, jsonify, render_template
from flask.logging import default_handler
from threading import Thread
import uuid
from datetime import datetime

from youtube_processor import YouTubeProcessor
from cloudinary_uploader import CloudinaryUploader
from task_manager import TaskManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Initialize components
youtube_processor = YouTubeProcessor()
cloudinary_uploader = CloudinaryUploader()
task_manager = TaskManager()

@app.route('/')
def index():
    """Render the main interface for testing the API"""
    return render_template('index.html')

@app.route('/api/process_video', methods=['POST'])
def process_video():
    """Process a single YouTube video"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url = data['url']
        task_id = str(uuid.uuid4())
        
        # Start background processing
        thread = Thread(target=_process_video_background, args=(task_id, url))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'status': 'processing',
            'message': 'Video processing started'
        })
        
    except Exception as e:
        app.logger.error(f"Error in process_video: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/process_playlist', methods=['POST'])
def process_playlist():
    """Process a YouTube playlist with pagination"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url = data['url']
        skip = data.get('skip', 0)
        limit = data.get('limit', 10)
        task_id = str(uuid.uuid4())
        
        # Start background processing
        thread = Thread(target=_process_playlist_background, args=(task_id, url, skip, limit))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'status': 'processing',
            'message': 'Playlist processing started',
            'skip': skip,
            'limit': limit
        })
        
    except Exception as e:
        app.logger.error(f"Error in process_playlist: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/process_channel', methods=['POST'])
def process_channel():
    """Process a YouTube channel with pagination"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url = data['url']
        skip = data.get('skip', 0)
        limit = data.get('limit', 10)
        task_id = str(uuid.uuid4())
        
        # Start background processing
        thread = Thread(target=_process_channel_background, args=(task_id, url, skip, limit))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'status': 'processing',
            'message': 'Channel processing started',
            'skip': skip,
            'limit': limit
        })
        
    except Exception as e:
        app.logger.error(f"Error in process_channel: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get the status of a processing task with essential details only"""
    try:
        status = task_manager.get_task_status(task_id)
        if not status:
            return jsonify({'error': 'Task not found'}), 404
        
        # Return only essential details for specific task
        essential_status = {
            'id': status['id'],
            'status': status['status'],
            'message': status['message'],
            'updated_at': status['updated_at']
        }
        
        # Add progress if available
        if 'progress' in status and status['progress']:
            essential_status['progress'] = status['progress']
        
        # Add error if failed
        if status['status'] == 'failed' and 'error' in status:
            essential_status['error'] = status['error']
        
        return jsonify(essential_status)
        
    except Exception as e:
        app.logger.error(f"Error in get_task_status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tasks', methods=['GET'])
def get_all_tasks():
    """Get all tasks and their statuses"""
    try:
        tasks = task_manager.get_all_tasks()
        return jsonify({'tasks': tasks})
        
    except Exception as e:
        app.logger.error(f"Error in get_all_tasks: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def _process_video_background(task_id, url):
    """Background function to process a single video"""
    try:
        task_manager.update_task(task_id, 'processing', 'Extracting video information...')
        
        # Extract video info
        video_info = youtube_processor.extract_video_info(url)
        if not video_info:
            task_manager.update_task(task_id, 'failed', 'Failed to extract video information')
            return
        
        # Check if song already exists
        task_manager.update_task(task_id, 'processing', 'Checking if song already exists...')
        if youtube_processor.check_song_exists(video_info['id'], video_info['title']):
            task_manager.update_task(task_id, 'completed', 'Song already exists, skipping processing')
            return
        
        # Download audio and thumbnail
        task_manager.update_task(task_id, 'processing', 'Downloading audio and thumbnail...')
        audio_path, thumbnail_path = youtube_processor.download_media(video_info)
        
        if not audio_path:
            task_manager.update_task(task_id, 'failed', 'Failed to download audio')
            return
        
        # Upload to Cloudinary
        task_manager.update_task(task_id, 'processing', 'Uploading to Cloudinary...')
        song_url, cover_url = cloudinary_uploader.upload_media(audio_path, thumbnail_path, video_info)
        
        if not song_url:
            task_manager.update_task(task_id, 'failed', 'Failed to upload to Cloudinary')
            return
        
        # Send to external API
        task_manager.update_task(task_id, 'processing', 'Sending to external API...')
        success = youtube_processor.send_to_external_api(video_info, song_url, cover_url)
        
        if success:
            task_manager.update_task(task_id, 'completed', 'Video processed successfully', {
                'video_info': video_info,
                'song_url': song_url,
                'cover_url': cover_url
            })
        else:
            task_manager.update_task(task_id, 'failed', 'Failed to send to external API')
            
    except Exception as e:
        app.logger.error(f"Error in background processing: {str(e)}")
        task_manager.update_task(task_id, 'failed', f'Processing error: {str(e)}')

def _process_playlist_background(task_id, url, skip, limit):
    """Background function to process a playlist"""
    try:
        task_manager.update_task(task_id, 'processing', 'Extracting playlist information...')
        
        videos = youtube_processor.extract_playlist_videos(url, skip, limit)
        if not videos:
            task_manager.update_task(task_id, 'failed', 'Failed to extract playlist videos')
            return
        
        total_videos = len(videos)
        processed = 0
        successful = 0
        
        for i, video_info in enumerate(videos):
            task_manager.update_task(task_id, 'processing', 
                f'Processing video {i+1}/{total_videos}: {video_info["title"]}', 
                {'progress': f'{i+1}/{total_videos}'})
            
            try:
                # Check if song already exists
                if youtube_processor.check_song_exists(video_info['id'], video_info['title']):
                    app.logger.info(f"Song {video_info['title']} already exists, skipping")
                    processed += 1
                    continue
                
                # Download and process
                audio_path, thumbnail_path = youtube_processor.download_media(video_info)
                if audio_path:
                    song_url, cover_url = cloudinary_uploader.upload_media(audio_path, thumbnail_path, video_info)
                    if song_url:
                        if youtube_processor.send_to_external_api(video_info, song_url, cover_url):
                            successful += 1
                
                processed += 1
                
            except Exception as e:
                app.logger.error(f"Error processing video {video_info['title']}: {str(e)}")
                processed += 1
        
        task_manager.update_task(task_id, 'completed', 
            f'Playlist processed: {successful}/{processed} videos successful', 
            {'total': total_videos, 'processed': processed, 'successful': successful})
            
    except Exception as e:
        app.logger.error(f"Error in playlist processing: {str(e)}")
        task_manager.update_task(task_id, 'failed', f'Playlist processing error: {str(e)}')

def _process_channel_background(task_id, url, skip, limit):
    """Background function to process a channel"""
    try:
        task_manager.update_task(task_id, 'processing', 'Extracting channel videos...')
        
        videos = youtube_processor.extract_channel_videos(url, skip, limit)
        if not videos:
            task_manager.update_task(task_id, 'failed', 'Failed to extract channel videos')
            return
        
        total_videos = len(videos)
        processed = 0
        successful = 0
        
        for i, video_info in enumerate(videos):
            task_manager.update_task(task_id, 'processing', 
                f'Processing video {i+1}/{total_videos}: {video_info["title"]}', 
                {'progress': f'{i+1}/{total_videos}'})
            
            try:
                # Check if song already exists
                if youtube_processor.check_song_exists(video_info['id'], video_info['title']):
                    app.logger.info(f"Song {video_info['title']} already exists, skipping")
                    processed += 1
                    continue
                
                # Download and process
                audio_path, thumbnail_path = youtube_processor.download_media(video_info)
                if audio_path:
                    song_url, cover_url = cloudinary_uploader.upload_media(audio_path, thumbnail_path, video_info)
                    if song_url:
                        if youtube_processor.send_to_external_api(video_info, song_url, cover_url):
                            successful += 1
                
                processed += 1
                
            except Exception as e:
                app.logger.error(f"Error processing video {video_info['title']}: {str(e)}")
                processed += 1
        
        task_manager.update_task(task_id, 'completed', 
            f'Channel processed: {successful}/{processed} videos successful', 
            {'total': total_videos, 'processed': processed, 'successful': successful})
            
    except Exception as e:
        app.logger.error(f"Error in channel processing: {str(e)}")
        task_manager.update_task(task_id, 'failed', f'Channel processing error: {str(e)}')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
