import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def create_task(self, task_id: str, task_type: str, description: str = ""):
        """Create a new task"""
        with self.lock:
            now = datetime.now(timezone.utc)
            self.tasks[task_id] = {
                'id': task_id,
                'type': task_type,
                'status': 'created',
                'description': description,
                'message': 'Task created',
                'created_at': now.isoformat(),
                'updated_at': now.isoformat(),
                'progress': None,
                'result': None,
                'error': None,
                'detailed_status': 'initiated',
                'counters': {
                    'total': 0,
                    'processed': 0,
                    'success': 0,
                    'error': 0,
                    'exists': 0,
                    'skipped_duration': 0,
                    'pending': 0
                },
                'last_video_status': None
            }

    def update_task(self, task_id: str, status: str, message: str = "", result: Any = None, error: str = None, detailed_status: str = None, progress_data: Dict = None):
        """Update task status and information"""
        with self.lock:
            now = datetime.now(timezone.utc)
            
            if task_id not in self.tasks:
                # Create task if it doesn't exist
                self.tasks[task_id] = {
                    'id': task_id,
                    'type': 'unknown',
                    'status': status,
                    'description': '',
                    'message': message,
                    'created_at': now.isoformat(),
                    'updated_at': now.isoformat(),
                    'progress': None,
                    'result': None,
                    'error': None,
                    'detailed_status': detailed_status or 'processing',
                    'counters': {
                        'total': 0,
                        'processed': 0,
                        'success': 0,
                        'error': 0,
                        'exists': 0,
                        'skipped_duration': 0,
                        'pending': 0
                    },
                    'last_video_status': None
                }
            
            task = self.tasks[task_id]
            task['status'] = status
            task['message'] = message
            task['updated_at'] = now.isoformat()
            
            if detailed_status:
                task['detailed_status'] = detailed_status
            
            if result is not None:
                task['result'] = result
            
            if error is not None:
                task['error'] = error
            
            if progress_data:
                task['progress'] = progress_data.get('progress', task.get('progress'))
                if 'counters' in progress_data:
                    task['counters'].update(progress_data['counters'])
                if 'last_video_status' in progress_data:
                    task['last_video_status'] = progress_data['last_video_status']

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a task"""
        with self.lock:
            return self.tasks.get(task_id, None)

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all tasks"""
        with self.lock:
            return self.tasks.copy()

    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                return True
            return False

    def cleanup_completed_tasks(self, max_tasks: int = 100):
        """Clean up old completed tasks to prevent memory bloat"""
        with self.lock:
            if len(self.tasks) > max_tasks:
                # Sort by updated_at and keep only the most recent tasks
                sorted_tasks = sorted(
                    self.tasks.items(),
                    key=lambda x: x[1]['updated_at'],
                    reverse=True
                )
                
                # Keep only the most recent tasks
                self.tasks = dict(sorted_tasks[:max_tasks])

    def get_tasks_by_status(self, status: str) -> Dict[str, Dict[str, Any]]:
        """Get all tasks with a specific status"""
        with self.lock:
            return {
                task_id: task for task_id, task in self.tasks.items()
                if task['status'] == status
            }

    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all active (processing) tasks"""
        with self.lock:
            return {
                task_id: task for task_id, task in self.tasks.items()
                if task['status'] in ['created', 'processing']
            }
