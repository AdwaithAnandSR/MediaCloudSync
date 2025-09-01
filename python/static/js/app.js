class YouTubeProcessor {
    constructor() {
        this.activeTasks = new Set();
        this.init();
    }

    init() {
        // Bind form events
        document.getElementById('videoForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.processVideo();
        });

        document.getElementById('playlistForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.processPlaylist();
        });

        document.getElementById('channelForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.processChannel();
        });

        document.getElementById('refreshTasks').addEventListener('click', () => {
            this.refreshTaskStatus();
        });

        // Auto-refresh task status every 5 seconds
        setInterval(() => {
            if (this.activeTasks.size > 0) {
                this.refreshTaskStatus();
            }
        }, 5000);

        // Load initial task status
        this.refreshTaskStatus();
    }

    async processVideo() {
        const url = document.getElementById('videoUrl').value.trim();
        
        if (!url) {
            this.showToast('Please enter a valid YouTube URL', 'error');
            return;
        }

        const button = document.querySelector('#videoForm button');
        this.setButtonLoading(button, true);

        try {
            const response = await fetch('/api/process_video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url })
            });

            const data = await response.json();

            if (response.ok) {
                this.activeTasks.add(data.task_id);
                this.showToast(`Video processing started. Task ID: ${data.task_id}`, 'success');
                this.addTaskToDisplay(data);
                document.getElementById('videoUrl').value = '';
            } else {
                this.showToast(data.error || 'Failed to process video', 'error');
            }
        } catch (error) {
            this.showToast('Network error occurred', 'error');
        } finally {
            this.setButtonLoading(button, false);
        }
    }

    async processPlaylist() {
        const url = document.getElementById('playlistUrl').value.trim();
        const skip = parseInt(document.getElementById('playlistSkip').value) || 0;
        const limit = parseInt(document.getElementById('playlistLimit').value) || 10;

        if (!url) {
            this.showToast('Please enter a valid playlist URL or ID', 'error');
            return;
        }

        const button = document.querySelector('#playlistForm button');
        this.setButtonLoading(button, true);

        try {
            const response = await fetch('/api/process_playlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url, skip, limit })
            });

            const data = await response.json();

            if (response.ok) {
                this.activeTasks.add(data.task_id);
                this.showToast(`Playlist processing started. Task ID: ${data.task_id}`, 'success');
                this.addTaskToDisplay(data);
                document.getElementById('playlistUrl').value = '';
            } else {
                this.showToast(data.error || 'Failed to process playlist', 'error');
            }
        } catch (error) {
            this.showToast('Network error occurred', 'error');
        } finally {
            this.setButtonLoading(button, false);
        }
    }

    async processChannel() {
        const url = document.getElementById('channelUrl').value.trim();
        const skip = parseInt(document.getElementById('channelSkip').value) || 0;
        const limit = parseInt(document.getElementById('channelLimit').value) || 10;

        if (!url) {
            this.showToast('Please enter a valid channel URL or handle', 'error');
            return;
        }

        const button = document.querySelector('#channelForm button');
        this.setButtonLoading(button, true);

        try {
            const response = await fetch('/api/process_channel', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url, skip, limit })
            });

            const data = await response.json();

            if (response.ok) {
                this.activeTasks.add(data.task_id);
                this.showToast(`Channel processing started. Task ID: ${data.task_id}`, 'success');
                this.addTaskToDisplay(data);
                document.getElementById('channelUrl').value = '';
            } else {
                this.showToast(data.error || 'Failed to process channel', 'error');
            }
        } catch (error) {
            this.showToast('Network error occurred', 'error');
        } finally {
            this.setButtonLoading(button, false);
        }
    }

    async refreshTaskStatus() {
        try {
            const response = await fetch('/api/tasks');
            const data = await response.json();

            if (response.ok) {
                this.updateTaskDisplay(data.tasks);
            }
        } catch (error) {
            console.error('Error refreshing task status:', error);
        }
    }

    updateTaskDisplay(tasks) {
        const container = document.getElementById('taskStatus');
        
        if (Object.keys(tasks).length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No tasks found</p>';
            return;
        }

        // Sort tasks by creation time (newest first)
        const sortedTasks = Object.values(tasks).sort((a, b) => 
            new Date(b.created_at) - new Date(a.created_at)
        );

        container.innerHTML = sortedTasks.map(task => this.createTaskCard(task)).join('');

        // Update active tasks set
        this.activeTasks.clear();
        sortedTasks.forEach(task => {
            if (task.status === 'processing' || task.status === 'created') {
                this.activeTasks.add(task.id);
            }
        });
    }

    createTaskCard(task) {
        const statusClass = this.getStatusClass(task.status);
        const statusIcon = this.getStatusIcon(task.status);
        const createdAt = new Date(task.created_at).toLocaleString();
        const updatedAt = new Date(task.updated_at).toLocaleString();

        return `
            <div class="card mb-3">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <div>
                        <span class="badge ${statusClass} me-2">
                            <i class="${statusIcon} me-1"></i>
                            ${task.status.toUpperCase()}
                        </span>
                        <small class="text-muted">Task ID: ${task.id}</small>
                    </div>
                    <small class="text-muted">Created: ${createdAt}</small>
                </div>
                <div class="card-body">
                    <p class="mb-2">${task.message}</p>
                    ${this.renderProgressAndCounters(task)}
                    <small class="text-muted">Last updated: ${updatedAt}</small>
                    ${task.result ? this.renderTaskResult(task.result) : ''}
                    ${task.error ? `<div class="alert alert-danger mt-2"><strong>Error:</strong> ${task.error}</div>` : ''}
                </div>
            </div>
        `;
    }

    renderProgressAndCounters(task) {
        let html = '';
        
        // Show progress if available
        if (task.progress) {
            html += `<p class="mb-2"><strong>Progress:</strong> ${task.progress}</p>`;
        }
        
        // Show detailed status if available
        if (task.detailed_status) {
            const statusText = this.formatDetailedStatus(task.detailed_status);
            html += `<p class="mb-2"><strong>Current Status:</strong> ${statusText}</p>`;
        }
        
        // Show last video status if available
        if (task.last_video_status) {
            const lastStatusText = this.formatLastVideoStatus(task.last_video_status);
            html += `<p class="mb-2"><strong>Last Video:</strong> ${lastStatusText}</p>`;
        }
        
        // Show counters if available
        if (task.counters) {
            const counters = task.counters;
            html += `
                <div class="mt-2">
                    <h6>Status Counters:</h6>
                    <div class="row">
                        <div class="col-md-6">
                            <ul class="list-unstyled mb-2">
                                <li><strong>Total:</strong> ${counters.total}</li>
                                <li><strong>Pending:</strong> ${counters.pending}</li>
                                <li><strong>Success:</strong> <span class="text-success">${counters.success}</span></li>
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <ul class="list-unstyled mb-2">
                                <li><strong>Already Exists:</strong> <span class="text-info">${counters.exists}</span></li>
                                <li><strong>Duration Skipped:</strong> <span class="text-warning">${counters.skipped_duration}</span></li>
                                <li><strong>Errors:</strong> <span class="text-danger">${counters.error}</span></li>
                            </ul>
                        </div>
                    </div>
                </div>
            `;
        }
        
        return html;
    }

    formatDetailedStatus(status) {
        const statusMap = {
            'initiated': 'Task Initiated',
            'extracting_info': 'Extracting Video Information',
            'extracting_playlist': 'Extracting Playlist Videos',
            'extracting_channel': 'Extracting Channel Videos',
            'checking_exists': 'Checking if Song Exists',
            'downloading': 'Downloading Audio & Thumbnail',
            'uploading': 'Uploading to Cloud Storage',
            'sending_to_api': 'Sending to Music API',
            'processing_video': 'Processing Video',
            'completed': 'Completed'
        };
        return statusMap[status] || status;
    }

    formatLastVideoStatus(status) {
        const statusMap = {
            'success': '<span class="text-success">Successfully Processed</span>',
            'error': '<span class="text-danger">Processing Failed</span>',
            'exists': '<span class="text-info">Already Exists</span>',
            'skipped_duration': '<span class="text-warning">Skipped (Duration)</span>'
        };
        return statusMap[status] || status;
    }

    renderTaskResult(result) {
        if (result.video_info) {
            return `
                <div class="mt-3">
                    <h6>Processed Successfully:</h6>
                    <ul class="list-unstyled">
                        <li><strong>Title:</strong> ${result.video_info.title}</li>
                        <li><strong>Artist:</strong> ${result.video_info.artist}</li>
                        <li><strong>Duration:</strong> ${this.formatDuration(result.video_info.duration)}</li>
                        ${result.song_url ? `<li><strong>Song URL:</strong> <a href="${result.song_url}" target="_blank" class="text-decoration-none">View <i class="fas fa-external-link-alt"></i></a></li>` : ''}
                        ${result.cover_url ? `<li><strong>Cover URL:</strong> <a href="${result.cover_url}" target="_blank" class="text-decoration-none">View <i class="fas fa-external-link-alt"></i></a></li>` : ''}
                    </ul>
                </div>
            `;
        }

        if (result.total !== undefined) {
            return `
                <div class="mt-3">
                    <h6>Final Results Summary:</h6>
                    <ul class="list-unstyled">
                        <li><strong>Total Videos:</strong> ${result.total}</li>
                        <li><strong>Successful:</strong> <span class="text-success">${result.successful}</span></li>
                        <li><strong>Success Rate:</strong> ${((result.successful / result.total) * 100).toFixed(1)}%</li>
                    </ul>
                </div>
            `;
        }

        return '';
    }

    addTaskToDisplay(taskData) {
        // This will be updated by the next refresh cycle
        setTimeout(() => this.refreshTaskStatus(), 1000);
    }

    getStatusClass(status) {
        switch (status) {
            case 'completed': return 'bg-success';
            case 'failed': return 'bg-danger';
            case 'processing': return 'bg-warning';
            case 'created': return 'bg-info';
            default: return 'bg-secondary';
        }
    }

    getStatusIcon(status) {
        switch (status) {
            case 'completed': return 'fas fa-check-circle';
            case 'failed': return 'fas fa-times-circle';
            case 'processing': return 'fas fa-spinner fa-spin';
            case 'created': return 'fas fa-clock';
            default: return 'fas fa-question-circle';
        }
    }

    formatDuration(seconds) {
        if (!seconds) return 'Unknown';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = seconds % 60;

        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        }
    }

    setButtonLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            const originalText = button.innerHTML;
            button.dataset.originalText = originalText;
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        } else {
            button.disabled = false;
            button.innerHTML = button.dataset.originalText || button.innerHTML;
        }
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('responseToast');
        const toastBody = toast.querySelector('.toast-body');
        const toastHeader = toast.querySelector('.toast-header');

        // Update toast styling based on type
        toast.className = 'toast';
        if (type === 'success') {
            toast.classList.add('text-bg-success');
            toastHeader.querySelector('i').className = 'fas fa-check-circle me-2';
        } else if (type === 'error') {
            toast.classList.add('text-bg-danger');
            toastHeader.querySelector('i').className = 'fas fa-exclamation-circle me-2';
        } else {
            toast.classList.add('text-bg-info');
            toastHeader.querySelector('i').className = 'fas fa-info-circle me-2';
        }

        toastBody.textContent = message;

        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new YouTubeProcessor();
});
