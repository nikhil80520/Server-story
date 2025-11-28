# Story Generation Queue Management System

## Overview
The enhanced background service now includes robust queue management features to ensure story generation is production-ready with automatic failure recovery, worker failover, and graceful error handling.

## Key Features

### 1. **Job Status Tracking**
Jobs progress through the following states:
- `QUEUED`: Job submitted and waiting for worker
- `RUNNING`: Worker actively processing the job
- `COMPLETED`: Job finished successfully
- `FAILED`: Job failed permanently (after retries)
- `TIMEOUT`: Job exceeded maximum execution time
- `RETRYING`: Job failed but is being retried
- `ABANDONED`: Job exceeded maximum retry attempts

### 2. **Priority Queue System**
- Jobs are ordered by: `(priority, timestamp, job)`
- Lower priority numbers = higher priority
- Timestamp ensures FIFO for same-priority jobs
- Default priority: 5 (normal)
- Failed jobs re-queued at priority 10 (lower)

### 3. **Worker Failover**
- Multiple workers (default: 5) process jobs concurrently
- If a worker crashes, the job is automatically re-queued
- Active job tracking prevents job loss during failures
- Graceful shutdown preserves in-flight jobs

### 4. **Timeout Detection**
- **Job Timeout**: 20 minutes (1200 seconds) maximum per job
- **Monitoring Interval**: Checks every 60 seconds
- **Heartbeat Mechanism**: Workers send heartbeat every 30 seconds
- **Stalled Detection**: 3 missed heartbeats (90 seconds) triggers timeout

### 5. **Automatic Retry Logic**
- **Maximum Retries**: 2 attempts per job
- **Retryable Errors**: Connection issues, timeouts, rate limits, 5xx errors
- **Non-Retryable Errors**: Invalid input, authentication errors, 4xx errors
- **Priority Reduction**: Retried jobs get lower priority to prevent blocking

### 6. **Graceful Error Handling**
- All errors caught and logged with context
- Callbacks notify clients of failure reasons
- Story status updated in database on failure
- Error messages truncated to 500 chars for storage

### 7. **Health Monitoring**
The `get_stats()` endpoint provides comprehensive metrics:
```json
{
    "service_running": true,
    "active_workers": 5,
    "active_jobs_count": 3,
    "total_jobs": 150,
    "completed_jobs": 140,
    "failed_jobs": 5,
    "running_jobs": 3,
    "queued_jobs": 2,
    "timeout_jobs": 1,
    "retrying_jobs": 1,
    "abandoned_jobs": 2,
    "jobs_with_retries": 8,
    "total_retries": 12,
    "success_rate": 93.3
}
```

## Configuration

### Timing Constants
```python
heartbeat_interval = 30  # seconds - worker liveness indicator
job_timeout_check_interval = 60  # seconds - how often to check for timeouts
job_timeout_seconds = 1200  # seconds (20 min) - max time per job
story_generation_timeout = 900  # seconds (15 min) - max time for parallel service
max_retries = 2  # attempts - maximum retry attempts per job
```

### Worker Configuration
```python
max_workers = 5  # concurrent workers processing jobs
```

## Usage

### Submitting a Job
```python
job = await enhanced_background_service.submit_story_job(
    story_id="story-123",
    user_id="user-456",
    parameters={
        "user_prompt": "A story about...",
        "voice_clone_id": "optional-voice-id",
        # ... other parameters
    },
    services={
        "story_service": story_service,
        "media_service": media_service,
        "storage_service": storage_service
    },
    callbacks={
        "on_progress": progress_callback,
        "on_completion": completion_callback
    },
    priority=5  # optional, default is 5
)
```

### Monitoring Job Status
```python
# Get job status
status = enhanced_background_service.get_job_status("job-id")

# Get service statistics
stats = enhanced_background_service.get_stats()

# Check result (if completed)
result = enhanced_background_service.get_job_result("job-id")
```

## Error Handling

### Retryable Errors
Errors containing these keywords trigger automatic retry:
- `timeout`
- `connection`
- `network`
- `rate limit`
- `503`, `502`, `504`
- `temporary`
- `unavailable`

### Non-Retryable Errors
All other errors are considered permanent and trigger immediate failure callback.

### Failure Callbacks
On permanent failure, the `on_completion` callback receives:
```python
{
    "status": "failed",
    "error": "Error message...",
    "story_id": "story-123",
    "attempts": 3  # total attempts made
}
```

## Operational Guidelines

### Normal Operation
1. Service starts with N workers
2. Jobs submitted to priority queue
3. Workers pull jobs in priority/FIFO order
4. Heartbeats sent every 30 seconds
5. Monitor task checks for timeouts every 60 seconds
6. Completed jobs remain in memory for 24 hours

### Failure Recovery
1. **Worker Crash**: Job automatically re-queued for another worker
2. **Timeout**: Job cancelled and retried (if retries remain)
3. **Transient Error**: Job immediately retried with lower priority
4. **Permanent Error**: Callbacks notified, story marked failed

### Graceful Shutdown
1. Service receives stop signal
2. Monitoring task cancelled
3. All workers receive cancellation signal
4. In-flight jobs re-queued to priority queue
5. Workers complete their shutdown
6. Service fully stopped

## Monitoring Best Practices

### Key Metrics to Watch
- **Success Rate**: Should be >95%
- **Timeout Jobs**: Should be <2% of total
- **Abandoned Jobs**: Should be <1% of total
- **Queue Size**: Should stay <10 under normal load
- **Active Jobs**: Should equal or be less than worker count

### Alert Thresholds
- ⚠️ **Warning**: Success rate <95%
- 🚨 **Critical**: Success rate <90%
- ⚠️ **Warning**: Queue size >20
- 🚨 **Critical**: Queue size >50
- ⚠️ **Warning**: Active workers <50% of max
- 🚨 **Critical**: Active workers = 0 while service running

## Testing Recommendations

### Test Scenarios
1. **Normal Operation**: Submit 10 jobs, verify all complete
2. **Worker Failover**: Kill worker mid-job, verify another picks it up
3. **Timeout Handling**: Simulate stuck job, verify timeout triggers retry
4. **Retry Logic**: Trigger retryable error, verify automatic retry
5. **Max Retries**: Trigger error 3 times, verify job abandoned
6. **Priority Queue**: Submit mixed priority jobs, verify order
7. **Graceful Shutdown**: Stop service mid-processing, verify jobs preserved

### Load Testing
- **Light Load**: 5 concurrent jobs (1x workers)
- **Normal Load**: 10 concurrent jobs (2x workers)
- **Heavy Load**: 25 concurrent jobs (5x workers)
- **Stress Test**: 50+ concurrent jobs (10x workers)

## Future Enhancements

### Potential Improvements
1. **Persistent Queue**: Save queue to Redis for cross-server recovery
2. **Dynamic Scaling**: Auto-adjust worker count based on queue size
3. **Job Priority Updates**: Allow priority changes for queued jobs
4. **Detailed Metrics**: Track per-scene performance, bottlenecks
5. **Dead Letter Queue**: Separate queue for permanently failed jobs
6. **Rate Limiting**: Prevent queue flooding from single user
7. **Job Cancellation**: API to cancel queued/running jobs
8. **Scheduled Jobs**: Support for delayed/scheduled execution

## Troubleshooting

### Jobs Not Completing
1. Check service is running: `stats['service_running']`
2. Check worker count: `stats['active_workers']`
3. Check for timeout jobs: `stats['timeout_jobs']`
4. Review error logs for patterns

### High Failure Rate
1. Check for retryable vs non-retryable errors
2. Review external service availability (Cartesia, SeeDream)
3. Check timeout settings are appropriate
4. Verify database connectivity

### Queue Backing Up
1. Check worker count is appropriate for load
2. Review job complexity and duration
3. Consider increasing worker count
4. Check for stuck jobs via heartbeat monitoring

### Memory Issues
1. Run cleanup periodically: `cleanup_old_jobs(max_age_hours=24)`
2. Monitor total_jobs count
3. Consider shorter retention period
4. Implement job result streaming instead of full storage

## Related Files
- `app/services/enhanced_background_service.py` - Main implementation
- `app/services/parallel_story_service.py` - Story generation logic
- `app/routers/stories.py` - API endpoints using the service
- `app/services/media_service.py` - Audio/image generation
- `app/services/storage_service.py` - Database operations
