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
        # Initialize counters
        counters = {'total': 1, 'processed': 0, 'success': 0, 'error': 0, 'exists': 0, 'skipped_duration': 0, 'pending': 1}
        
        task_manager.update_task(task_id, 'processing', 'Extracting video information...', 
                                detailed_status='extracting_info', 
                                progress_data={'counters': counters})
        
        # Extract video info
        video_info = youtube_processor.extract_video_info(url)
        if not video_info:
            counters.update({'error': 1, 'pending': 0})
            task_manager.update_task(task_id, 'failed', 'Failed to extract video information',
                                   progress_data={'counters': counters, 'last_video_status': 'error'})
            return
        
        # Check duration filter
        if not youtube_processor.is_duration_valid(video_info['duration']):
            counters.update({'skipped_duration': 1, 'pending': 0})
            duration_min = video_info['duration'] / 60 if video_info['duration'] else 0
            task_manager.update_task(task_id, 'completed', 
                                   f'Video skipped - duration {duration_min:.1f} min (must be 2-8 min)',
                                   progress_data={'counters': counters, 'last_video_status': 'skipped_duration'})
            return
        
        # Check if song already exists
        task_manager.update_task(task_id, 'processing', 'Checking if song already exists...',
                                detailed_status='checking_exists')
        if youtube_processor.check_song_exists(video_info['id'], video_info['title']):
            counters.update({'exists': 1, 'pending': 0})
            task_manager.update_task(task_id, 'completed', 'Song already exists, skipping processing',
                                   progress_data={'counters': counters, 'last_video_status': 'exists'})
            return
        
        # Download audio and thumbnail
        task_manager.update_task(task_id, 'processing', 'Downloading audio and thumbnail...',
                                detailed_status='downloading')
        audio_path, thumbnail_path = youtube_processor.download_media(video_info)
        
        if not audio_path:
            counters.update({'error': 1, 'pending': 0})
            task_manager.update_task(task_id, 'failed', 'Failed to download audio',
                                   progress_data={'counters': counters, 'last_video_status': 'error'})
            return
        
        # Upload to Cloudinary
        task_manager.update_task(task_id, 'processing', 'Uploading to Cloudinary...',
                                detailed_status='uploading')
        song_url, cover_url = cloudinary_uploader.upload_media(audio_path, thumbnail_path, video_info)
        
        if not song_url:
            counters.update({'error': 1, 'pending': 0})
            task_manager.update_task(task_id, 'failed', 'Failed to upload to Cloudinary',
                                   progress_data={'counters': counters, 'last_video_status': 'error'})
            return
        
        # Send to external API
        task_manager.update_task(task_id, 'processing', 'Sending to external API...',
                                detailed_status='sending_to_api')
        success = youtube_processor.send_to_external_api(video_info, song_url, cover_url)
        
        if success:
            counters.update({'success': 1, 'processed': 1, 'pending': 0})
            task_manager.update_task(task_id, 'completed', 'Video processed successfully', {
                'video_info': video_info,
                'song_url': song_url,
                'cover_url': cover_url
            }, progress_data={'counters': counters, 'last_video_status': 'success'})
        else:
            counters.update({'error': 1, 'pending': 0})
            task_manager.update_task(task_id, 'failed', 'Failed to send to external API',
                                   progress_data={'counters': counters, 'last_video_status': 'error'})
            
    except Exception as e:
        app.logger.error(f"Error in background processing: {str(e)}")
        counters = {'total': 1, 'processed': 0, 'success': 0, 'error': 1, 'exists': 0, 'skipped_duration': 0, 'pending': 0}
        task_manager.update_task(task_id, 'failed', f'Processing error: {str(e)}',
                               progress_data={'counters': counters, 'last_video_status': 'error'})

def _process_playlist_background(task_id, url, skip, limit):
    """Background function to process a playlist"""
    try:
        task_manager.update_task(task_id, 'processing', 'Extracting playlist information...',
                                detailed_status='extracting_playlist')
        
        videos = youtube_processor.extract_playlist_videos(url, skip, limit)
        if not videos:
            task_manager.update_task(task_id, 'failed', 'Failed to extract playlist videos')
            return
        
        total_videos = len(videos)
        counters = {
            'total': total_videos,
            'processed': 0,
            'success': 0,
            'error': 0,
            'exists': 0,
            'skipped_duration': 0,
            'pending': total_videos
        }
        
        for i, video_info in enumerate(videos):
            current_progress = f'{i+1}/{total_videos}'
            task_manager.update_task(task_id, 'processing', 
                f'Processing video {i+1}/{total_videos}: {video_info["title"]}',
                detailed_status='processing_video',
                progress_data={'progress': current_progress, 'counters': counters})
            
            try:
                # Check duration filter
                if not youtube_processor.is_duration_valid(video_info['duration']):
                    counters['skipped_duration'] += 1
                    counters['pending'] -= 1
                    app.logger.info(f"Video {video_info['title']} skipped - invalid duration")
                    task_manager.update_task(task_id, 'processing', 
                        f'Processing video {i+1}/{total_videos}: {video_info["title"]} (skipped - duration)',
                        progress_data={'last_video_status': 'skipped_duration', 'counters': counters})
                    continue
                
                # Check if song already exists
                if youtube_processor.check_song_exists(video_info['id'], video_info['title']):
                    counters['exists'] += 1
                    counters['pending'] -= 1
                    app.logger.info(f"Song {video_info['title']} already exists, skipping")
                    task_manager.update_task(task_id, 'processing', 
                        f'Processing video {i+1}/{total_videos}: {video_info["title"]} (exists)',
                        progress_data={'last_video_status': 'exists', 'counters': counters})
                    continue
                
                # Download and process
                audio_path, thumbnail_path = youtube_processor.download_media(video_info)
                if audio_path:
                    song_url, cover_url = cloudinary_uploader.upload_media(audio_path, thumbnail_path, video_info)
                    if song_url:
                        if youtube_processor.send_to_external_api(video_info, song_url, cover_url):
                            counters['success'] += 1
                            counters['processed'] += 1
                            counters['pending'] -= 1
                            task_manager.update_task(task_id, 'processing', 
                                f'Processing video {i+1}/{total_videos}: {video_info["title"]} (success)',
                                progress_data={'last_video_status': 'success', 'counters': counters})
                        else:
                            counters['error'] += 1
                            counters['pending'] -= 1
                            task_manager.update_task(task_id, 'processing', 
                                f'Processing video {i+1}/{total_videos}: {video_info["title"]} (api error)',
                                progress_data={'last_video_status': 'error', 'counters': counters})
                    else:
                        counters['error'] += 1
                        counters['pending'] -= 1
                        task_manager.update_task(task_id, 'processing', 
                            f'Processing video {i+1}/{total_videos}: {video_info["title"]} (upload error)',
                            progress_data={'last_video_status': 'error', 'counters': counters})
                else:
                    counters['error'] += 1
                    counters['pending'] -= 1
                    task_manager.update_task(task_id, 'processing', 
                        f'Processing video {i+1}/{total_videos}: {video_info["title"]} (download error)',
                        progress_data={'last_video_status': 'error', 'counters': counters})
                
            except Exception as e:
                counters['error'] += 1
                counters['pending'] -= 1
                app.logger.error(f"Error processing video {video_info['title']}: {str(e)}")
                task_manager.update_task(task_id, 'processing', 
                    f'Processing video {i+1}/{total_videos}: {video_info["title"]} (error)',
                    progress_data={'last_video_status': 'error', 'counters': counters})
        
        success_rate = (counters['success'] / counters['total'] * 100) if counters['total'] > 0 else 0
        task_manager.update_task(task_id, 'completed', 
            f'Playlist completed: {counters["success"]}/{counters["total"]} successful ({success_rate:.1f}%)', 
            {'total': counters['total'], 'processed': counters['processed'], 'successful': counters['success']},
            progress_data={'counters': counters})
            
    except Exception as e:
        app.logger.error(f"Error in playlist processing: {str(e)}")
        task_manager.update_task(task_id, 'failed', f'Playlist processing error: {str(e)}')

def _process_channel_background(task_id, url, skip, limit):
    """Background function to process a channel"""
    try:
        task_manager.update_task(task_id, 'processing', 'Extracting channel videos...',
                                detailed_status='extracting_channel')
        
        videos = youtube_processor.extract_channel_videos(url, skip, limit)
        if not videos:
            task_manager.update_task(task_id, 'failed', 'Failed to extract channel videos')
            return
        
        total_videos = len(videos)
        counters = {
            'total': total_videos,
            'processed': 0,
            'success': 0,
            'error': 0,
            'exists': 0,
            'skipped_duration': 0,
            'pending': total_videos
        }
        
        for i, video_info in enumerate(videos):
            current_progress = f'{i+1}/{total_videos}'
            task_manager.update_task(task_id, 'processing', 
                f'Processing video {i+1}/{total_videos}: {video_info["title"]}',
                detailed_status='processing_video',
                progress_data={'progress': current_progress, 'counters': counters})
            
            try:
                # Check duration filter
                if not youtube_processor.is_duration_valid(video_info['duration']):
                    counters['skipped_duration'] += 1
                    counters['pending'] -= 1
                    app.logger.info(f"Video {video_info['title']} skipped - invalid duration")
                    task_manager.update_task(task_id, 'processing', 
                        f'Processing video {i+1}/{total_videos}: {video_info["title"]} (skipped - duration)',
                        progress_data={'last_video_status': 'skipped_duration', 'counters': counters})
                    continue
                
                # Check if song already exists
                if youtube_processor.check_song_exists(video_info['id'], video_info['title']):
                    counters['exists'] += 1
                    counters['pending'] -= 1
                    app.logger.info(f"Song {video_info['title']} already exists, skipping")
                    task_manager.update_task(task_id, 'processing', 
                        f'Processing video {i+1}/{total_videos}: {video_info["title"]} (exists)',
                        progress_data={'last_video_status': 'exists', 'counters': counters})
                    continue
                
                # Download and process
                audio_path, thumbnail_path = youtube_processor.download_media(video_info)
                if audio_path:
                    song_url, cover_url = cloudinary_uploader.upload_media(audio_path, thumbnail_path, video_info)
                    if song_url:
                        if youtube_processor.send_to_external_api(video_info, song_url, cover_url):
                            counters['success'] += 1
                            counters['processed'] += 1
                            counters['pending'] -= 1
                            task_manager.update_task(task_id, 'processing', 
                                f'Processing video {i+1}/{total_videos}: {video_info["title"]} (success)',
                                progress_data={'last_video_status': 'success', 'counters': counters})
                        else:
                            counters['error'] += 1
                            counters['pending'] -= 1
                            task_manager.update_task(task_id, 'processing', 
                                f'Processing video {i+1}/{total_videos}: {video_info["title"]} (api error)',
                                progress_data={'last_video_status': 'error', 'counters': counters})
                    else:
                        counters['error'] += 1
                        counters['pending'] -= 1
                        task_manager.update_task(task_id, 'processing', 
                            f'Processing video {i+1}/{total_videos}: {video_info["title"]} (upload error)',
                            progress_data={'last_video_status': 'error', 'counters': counters})
                else:
                    counters['error'] += 1
                    counters['pending'] -= 1
                    task_manager.update_task(task_id, 'processing', 
                        f'Processing video {i+1}/{total_videos}: {video_info["title"]} (download error)',
                        progress_data={'last_video_status': 'error', 'counters': counters})
                
            except Exception as e:
                counters['error'] += 1
                counters['pending'] -= 1
                app.logger.error(f"Error processing video {video_info['title']}: {str(e)}")
                task_manager.update_task(task_id, 'processing', 
                    f'Processing video {i+1}/{total_videos}: {video_info["title"]} (error)',
                    progress_data={'last_video_status': 'error', 'counters': counters})
        
        success_rate = (counters['success'] / counters['total'] * 100) if counters['total'] > 0 else 0
        task_manager.update_task(task_id, 'completed', 
            f'Channel completed: {counters["success"]}/{counters["total"]} successful ({success_rate:.1f}%)', 
            {'total': counters['total'], 'processed': counters['processed'], 'successful': counters['success']},
            progress_data={'counters': counters})
            
    except Exception as e:
        app.logger.error(f"Error in channel processing: {str(e)}")
        task_manager.update_task(task_id, 'failed', f'Channel processing error: {str(e)}')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
