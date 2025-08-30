# YouTube Music Processor

A robust Python server application for extracting high-quality audio from YouTube videos, playlists, and channels with automatic cloud storage and external API integration.

## 🎵 Features

- **High-Quality Audio Extraction**: Downloads 320kbps MP3 audio using yt-dlp with FFmpeg
- **Duration Filtering**: Processes only videos between 2-8 minutes duration
- **Duplicate Detection**: Checks existing songs before processing to avoid duplicates
- **Cloud Storage**: Uploads audio and cover images to Cloudinary with organized structure
- **External API Integration**: Sends processed data to vivid-music.vercel.app
- **Batch Processing**: Handles playlists and channels with pagination support
- **Real-time Status Tracking**: Detailed progress monitoring with counters and status updates
- **Cookie Support**: Supports Netscape format cookies for authenticated access
- **Asynchronous Processing**: Non-blocking task execution with background processing

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- FFmpeg (automatically installed)
- Cloudinary account and API credentials

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   uv add yt-dlp requests python-dotenv cloudinary flask gunicorn
   ```

3. Set up environment variables (Cloudinary credentials):
   - `CLOUDINARY_CLOUD_NAME`
   - `CLOUDINARY_API_KEY`
   - `CLOUDINARY_API_SECRET`

4. Start the server:
   ```bash
   gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
   ```

## 📡 API Endpoints

### Process Single Video
```http
POST /api/process_video
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

### Process Playlist
```http
POST /api/process_playlist
Content-Type: application/json

{
  "url": "https://www.youtube.com/playlist?list=PLAYLIST_ID",
  "skip": 0,
  "limit": 10
}
```

### Process Channel
```http
POST /api/process_channel
Content-Type: application/json

{
  "url": "https://www.youtube.com/@channelname",
  "skip": 0,
  "limit": 10
}
```

### Task Status Tracking
```http
GET /api/tasks                    # Get all tasks with full details
GET /api/task_status/{task_id}    # Get specific task with essential details only
```

## 🏗️ Internal Architecture

### Core Components

#### 1. YouTube Processor (`youtube_processor.py`)
- **Video Information Extraction**: Uses yt-dlp to extract metadata (id, title, duration, artist)
- **Media Download**: Downloads high-quality audio (320kbps MP3) and thumbnails
- **Duration Validation**: Filters videos to 2-8 minute range
- **Cookie Support**: Validates and uses Netscape format cookies for authentication
- **External API Communication**: Interfaces with vivid-music.vercel.app

#### 2. Cloudinary Uploader (`cloudinary_uploader.py`)
- **Organized Storage**: Uploads audio to `songs/` and covers to `covers/` folders
- **Metadata Tagging**: Adds contextual information to uploaded files
- **Resource Type Management**: Uses video resource type for audio, image for covers
- **Automatic Cleanup**: Removes local files after successful upload

#### 3. Task Manager (`task_manager.py`)
- **Thread-Safe Operations**: Uses locks to prevent race conditions
- **UTC Timezone**: Proper timezone handling for accurate timestamps
- **Detailed Status Tracking**: Monitors processing stages (initiated, extracting, downloading, uploading, etc.)
- **Comprehensive Counters**: Tracks total, success, error, exists, skipped, pending counts
- **Memory Management**: Automatic cleanup of old completed tasks

#### 4. Flask Application (`app.py`)
- **RESTful API Design**: Clean endpoint structure for all operations
- **Asynchronous Processing**: Background threads for non-blocking operations
- **Error Handling**: Comprehensive exception handling with proper HTTP status codes
- **Real-time Updates**: Status tracking with detailed progress information

### Processing Pipeline

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Request  │───▶│  Extract Video   │───▶│ Duration Check  │
│                 │    │   Information    │    │   (2-8 min)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  External API   │◀───│  Upload to       │◀───│ Check if Song   │
│   Integration   │    │   Cloudinary     │    │    Exists       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                       ┌──────────────────┐    ┌─────────────────┐
                       │  Download Audio  │◀───│ Continue if New │
                       │  & Thumbnail     │    │      Song       │
                       └──────────────────┘    └─────────────────┘
```

### Data Flow

1. **Request Validation**: Validates input URLs and parameters
2. **Task Creation**: Creates unique task with UUID and initial status
3. **Background Processing**: Spawns daemon thread for processing
4. **Information Extraction**: Uses yt-dlp to extract video metadata
5. **Duration Filtering**: Validates video duration (120-480 seconds)
6. **Duplicate Detection**: Checks vivid-music.vercel.app API for existing songs
7. **Media Download**: Downloads high-quality audio and thumbnail
8. **Cloud Upload**: Uploads files to Cloudinary with organized structure
9. **API Integration**: Sends processed data to external music API
10. **Status Updates**: Real-time progress tracking throughout pipeline

### Status Tracking System

#### Detailed Status Types
- `initiated`: Task created and queued
- `extracting_info`: Extracting video information
- `extracting_playlist`: Extracting playlist videos
- `extracting_channel`: Extracting channel videos
- `checking_exists`: Checking if song already exists
- `downloading`: Downloading audio and thumbnail
- `uploading`: Uploading to Cloudinary
- `sending_to_api`: Sending data to external API
- `processing_video`: General video processing

#### Counter Categories
- `total`: Total number of videos to process
- `processed`: Successfully processed videos
- `success`: Successfully uploaded and sent to API
- `error`: Videos that failed during processing
- `exists`: Videos that already exist in the system
- `skipped_duration`: Videos outside 2-8 minute range
- `pending`: Videos waiting to be processed

#### Last Video Status
- `success`: Video processed successfully
- `error`: Processing failed
- `exists`: Song already exists
- `skipped_duration`: Skipped due to duration filter

## 🍪 Cookie Support

The application supports Netscape format cookies for accessing age-restricted or private content:

1. Place `cookies.txt` in the root directory
2. Ensure proper Netscape format (tab-separated values)
3. Application automatically validates and uses cookies if available
4. Invalid formats are logged but don't stop processing

### Cookie Format Example
```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	FALSE	1234567890	session_token	abc123def456
```

## 🔧 Configuration

### Environment Variables
```bash
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
SESSION_SECRET=your_session_secret_key
```

### Audio Quality Settings
- **Format**: Best available audio (m4a/mp3 preferred)
- **Quality**: 320kbps MP3 (audioquality: '0')
- **Codec**: MP3 with FFmpeg post-processing
- **Container**: MP3 output format

### Duration Filtering
- **Minimum**: 2 minutes (120 seconds)
- **Maximum**: 8 minutes (480 seconds)
- **Validation**: Checked before processing to save resources

## 📊 Monitoring and Logging

### Task Status API Response (Essential Details)
```json
{
  "id": "task-uuid",
  "status": "processing",
  "message": "Processing video 3/10: Song Title",
  "updated_at": "2025-08-30T05:30:58.123456+00:00",
  "progress": "3/10",
  "detailed_status": "uploading",
  "counters": {
    "total": 10,
    "processed": 2,
    "success": 2,
    "error": 0,
    "exists": 1,
    "skipped_duration": 0,
    "pending": 7
  },
  "last_video_status": "success"
}
```

### Full Task Status API Response
```json
{
  "id": "task-uuid",
  "type": "playlist",
  "status": "completed",
  "description": "Processing playlist",
  "message": "Playlist completed: 8/10 successful (80.0%)",
  "created_at": "2025-08-30T05:25:00.000000+00:00",
  "updated_at": "2025-08-30T05:30:58.123456+00:00",
  "detailed_status": "completed",
  "counters": {
    "total": 10,
    "processed": 10,
    "success": 8,
    "error": 1,
    "exists": 1,
    "skipped_duration": 0,
    "pending": 0
  },
  "result": {
    "total": 10,
    "processed": 10,
    "successful": 8
  }
}
```

## 🚦 Error Handling

### Common Error Types
- **Invalid URL**: Malformed or unsupported YouTube URLs
- **Duration Filter**: Videos outside 2-8 minute range
- **Download Failure**: Network issues or unavailable content
- **Upload Failure**: Cloudinary connection or quota issues
- **API Failure**: External API communication errors
- **Cookie Issues**: Invalid cookie format or authentication failure

### Error Recovery
- Automatic retry mechanisms for network failures
- Graceful degradation when thumbnails unavailable
- Cookie validation with fallback to unauthenticated access
- Comprehensive logging for debugging

## 📈 Performance Optimization

### Concurrent Processing
- Background thread processing for non-blocking operations
- Thread-safe task management with proper locking
- Efficient memory usage with automatic cleanup

### Resource Management
- Temporary file cleanup after processing
- Cloudinary upload with immediate local file removal
- Task history cleanup to prevent memory bloat
- Connection pooling for external API calls

### Caching Strategy
- Duplicate detection before expensive operations
- Efficient video information extraction
- Optimized playlist/channel pagination

## 🔗 External Integrations

### Vivid Music API
- **Duplicate Check**: `POST /checkSongExistsByYtId`
- **Song Addition**: `POST /addSong`
- **Data Format**: JSON with title, URLs, duration, artist information

### Cloudinary Storage
- **Audio Storage**: `songs/{video_id}` with video resource type
- **Cover Storage**: `covers/{video_id}` with image resource type
- **Metadata**: Contextual information including title, artist, duration

## 🛠️ Development

### Adding New Features
1. Update corresponding processor class
2. Modify task manager for new status types
3. Update API endpoints in Flask app
4. Add frontend JavaScript handling
5. Update documentation

### Testing
- Manual testing through web interface
- API testing with curl or Postman
- Task status monitoring through status endpoints
- Error simulation for robustness testing

## 📝 License

This project is for educational and personal use. Respect YouTube's Terms of Service and copyright laws when using this application.

---

*Built with ❤️ using Python, Flask, yt-dlp, and Cloudinary*