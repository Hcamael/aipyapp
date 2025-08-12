# AIPython Agent Mode

AIPython Agent Mode is an HTTP API server that enables integration with external systems like n8n workflows. It provides a RESTful API for submitting, executing, and monitoring AI-powered tasks.

## Overview

Agent Mode transforms AIPython from an interactive CLI tool into a programmable service that can:
- Accept task instructions via HTTP API
- Execute tasks asynchronously in the background
- Capture and return structured output
- Manage multiple concurrent tasks
- Provide task status monitoring and result retrieval

## Starting Agent Mode

### Command Line

```bash
python -m aipyapp --agent --host 127.0.0.1 --port 8848
```

### Parameters

- `--agent`: Enable Agent mode (required)
- `--host`: Server host address (default: 127.0.0.1)
- `--port`: Server port (default: 8848)
- `--config-dir`: Configuration directory
- `--role`: AI assistant role
- `--debug`: Enable debug logging

### Example Startup

```bash
🤖 AIPython Agent Mode (1.0.0)
🚀 Starting HTTP API server on 127.0.0.1:8848
✅ Agent manager initialized
🔗 API Documentation: http://127.0.0.1:8848/docs
📊 Health Check: http://127.0.0.1:8848/health
```

## API Endpoints

### Base Information

#### GET `/`
Returns API information and available endpoints.

**Response:**
```json
{
  "name": "AIPython Agent API",
  "version": "1.0.0",
  "status": "running",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "endpoints": {
    "submit_task": "POST /tasks",
    "get_task_status": "GET /tasks/{task_id}",
    "get_task_result": "GET /tasks/{task_id}/result",
    "list_tasks": "GET /tasks",
    "cancel_task": "DELETE /tasks/{task_id}",
    "health": "GET /health"
  }
}
```

#### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "agent_manager": "initialized"
}
```

### Task Management

#### POST `/tasks`
Submit a new task for execution.

**Request Body:**
```json
{
  "instruction": "Create a Python script to count lines in .txt files",
  "metadata": {
    "source": "n8n",
    "workflow_id": "workflow_123",
    "user": "john_doe"
  }
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Task submitted successfully"
}
```

#### GET `/tasks/{task_id}`
Get task status and basic information.

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "instruction": "Create a Python script to count lines in .txt files",
  "status": "completed",
  "created_at": "2024-01-01T12:00:00.000Z",
  "started_at": "2024-01-01T12:00:01.000Z",
  "completed_at": "2024-01-01T12:00:15.000Z",
  "error": null
}
```

#### GET `/tasks/{task_id}/result`
Get complete task result with captured output.

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "instruction": "Create a Python script to count lines in .txt files",
  "status": "completed",
  "created_at": "2024-01-01T12:00:00.000Z",
  "started_at": "2024-01-01T12:00:01.000Z",
  "completed_at": "2024-01-01T12:00:15.000Z",
  "error": null,
  "output": {
    "messages": [
      {
        "type": "task_start",
        "content": {
          "instruction": "Create a Python script to count lines in .txt files",
          "task_id": null
        },
        "timestamp": "2024-01-01T12:00:01.000Z"
      },
      {
        "type": "llm_response",
        "content": {
          "llm": "claude-3-5-sonnet-20241022",
          "message": "I'll create a Python script that counts lines in .txt files..."
        },
        "timestamp": "2024-01-01T12:00:05.000Z"
      }
    ],
    "results": [
      {
        "block_name": "count_lines.py",
        "language": "python",
        "result": {
          "status": "success",
          "output": "Script created successfully"
        }
      }
    ],
    "errors": [],
    "metadata": {
      "instruction": "Create a Python script to count lines in .txt files",
      "source": "n8n",
      "workflow_id": "workflow_123"
    }
  }
}
```

#### GET `/tasks`
List all tasks.

**Response:**
```json
{
  "tasks": {
    "550e8400-e29b-41d4-a716-446655440000": {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "instruction": "Create a Python script to count lines in .txt files",
      "status": "completed",
      "created_at": "2024-01-01T12:00:00.000Z",
      "started_at": "2024-01-01T12:00:01.000Z",
      "completed_at": "2024-01-01T12:00:15.000Z"
    }
  }
}
```

#### DELETE `/tasks/{task_id}`
Cancel a running task.

**Response:**
```json
{
  "message": "Task 550e8400-e29b-41d4-a716-446655440000 cancelled"
}
```

### Administration

#### POST `/admin/cleanup`
Clean up completed tasks older than specified hours.

**Parameters:**
- `max_age_hours`: Maximum age in hours (default: 24)

**Response:**
```json
{
  "message": "Cleaned up 5 tasks"
}
```

## Task Status States

- **pending**: Task submitted but not yet started
- **running**: Task currently executing
- **completed**: Task finished successfully
- **error**: Task failed with an error
- **cancelled**: Task was cancelled by user

## Output Structure

The Agent mode captures comprehensive execution information:

### Messages Array
Chronological log of all events during task execution:
- `task_start`: Task begins execution
- `llm_response`: AI model responses
- `exec_start`: Code block execution begins
- `exec_result`: Code execution results
- `error`: Error occurrences
- `task_end`: Task completion

### Results Array
Structured results from code executions:
- `block_name`: Name of executed code block
- `language`: Programming language used
- `result`: Execution outcome and output

### Errors Array
Any errors encountered during execution:
- `message`: Error description
- `exception`: Full exception details if available

### Metadata
Custom metadata provided with task submission plus execution context.

## Integration Examples

### n8n Integration

```javascript
// n8n HTTP Request Node Configuration
const taskSubmission = {
  method: 'POST',
  url: 'http://127.0.0.1:8848/tasks',
  headers: {
    'Content-Type': 'application/json'
  },
  body: {
    instruction: '{{$json["instruction"]}}',
    metadata: {
      source: 'n8n',
      workflow_id: '{{$workflow.id}}',
      execution_id: '{{$execution.id}}'
    }
  }
};

// Poll for completion
const pollResult = {
  method: 'GET',
  url: 'http://127.0.0.1:8848/tasks/{{$json["task_id"]}}/result'
};
```

### Python Client Example

```python
import requests
import time
import json

class AIPythonClient:
    def __init__(self, base_url='http://127.0.0.1:8848'):
        self.base_url = base_url
    
    def submit_task(self, instruction, metadata=None):
        response = requests.post(
            f'{self.base_url}/tasks',
            json={
                'instruction': instruction,
                'metadata': metadata or {}
            }
        )
        return response.json()
    
    def wait_for_completion(self, task_id, poll_interval=2):
        while True:
            response = requests.get(f'{self.base_url}/tasks/{task_id}')
            task = response.json()
            
            if task['status'] in ['completed', 'error', 'cancelled']:
                break
                
            time.sleep(poll_interval)
        
        # Get full results
        response = requests.get(f'{self.base_url}/tasks/{task_id}/result')
        return response.json()

# Usage
client = AIPythonClient()
task = client.submit_task('Create a data analysis script for CSV files')
result = client.wait_for_completion(task['task_id'])
print(json.dumps(result, indent=2))
```

### cURL Examples

```bash
# Submit task
curl -X POST http://127.0.0.1:8848/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Write a Python function to calculate fibonacci numbers",
    "metadata": {"source": "curl", "user": "developer"}
  }'

# Check status
curl http://127.0.0.1:8848/tasks/550e8400-e29b-41d4-a716-446655440000

# Get results
curl http://127.0.0.1:8848/tasks/550e8400-e29b-41d4-a716-446655440000/result

# List all tasks
curl http://127.0.0.1:8848/tasks

# Health check
curl http://127.0.0.1:8848/health
```

## Architecture

### Core Components

1. **AgentTaskManager**: Manages task lifecycle and execution
2. **DisplayAgent**: Captures all output and events for API response
3. **FastAPI Server**: Provides HTTP API endpoints
4. **ThreadPoolExecutor**: Handles concurrent task execution

### Event System

The Agent mode leverages AIPython's event system to capture:
- Task lifecycle events
- LLM interactions
- Code execution results
- Error occurrences
- System messages

### Concurrency

- Supports up to 4 concurrent task executions (configurable)
- Asynchronous API using FastAPI
- Thread-safe task management
- Background task execution

## Configuration

### Environment Variables

- `AIPYTHON_CONFIG_DIR`: Configuration directory path
- `AIPYTHON_DEBUG`: Enable debug logging
- `AIPYTHON_LANG`: Language setting

### Configuration Files

Agent mode uses the same configuration files as interactive mode:
- `config/llm.json`: LLM provider settings
- `config/settings.json`: General settings
- `config/role.txt`: System role definition

## Error Handling

### Common Error Responses

```json
{
  "detail": "Task 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

### HTTP Status Codes

- `200`: Success
- `404`: Task not found
- `400`: Invalid request or task cannot be cancelled
- `500`: Internal server error

### Task Error Handling

Failed tasks return detailed error information:

```json
{
  "status": "error",
  "error": "ImportError: No module named 'pandas'",
  "output": {
    "errors": [
      {
        "message": "ImportError: No module named 'pandas'",
        "exception": "ImportError: No module named 'pandas'"
      }
    ]
  }
}
```

## Performance Considerations

### Resource Management

- Maximum 4 concurrent tasks by default
- Automatic cleanup of completed tasks after 24 hours
- Memory-efficient output capture
- Streaming response support

### Scalability

- Stateless API design
- In-memory task storage (suitable for single-node deployment)
- Configurable thread pool size
- Efficient event handling

### Monitoring

- Health check endpoint for load balancer integration
- Structured logging with task IDs
- Execution time tracking
- Error rate monitoring

## Security Considerations

### Network Security

- Bind to localhost by default
- No built-in authentication (use reverse proxy)
- CORS not configured (add middleware if needed)

### Task Execution

- Inherits security model from AIPython runtime
- Code execution in same environment as server
- No sandboxing by default

### Recommendations

1. Use reverse proxy with authentication for production
2. Run in containerized environment
3. Monitor resource usage and set limits
4. Implement request rate limiting
5. Use network policies to restrict access

## Troubleshooting

### Common Issues

1. **Server won't start**: Check port availability and configuration
2. **Task hangs**: Check LLM configuration and network connectivity
3. **Empty output**: Verify DisplayAgent event registration
4. **Memory leaks**: Enable automatic task cleanup

### Debug Mode

Start with `--debug` flag for verbose logging:

```bash
python -m aipyapp --agent --debug --host 127.0.0.1 --port 8848
```

### Log Analysis

Agent mode uses structured logging with context:

```
INFO     | aipyapp.aipy.agent_taskmgr:81 - Task submitted: 550e8400-e29b-41d4-a716-446655440000
INFO     | aipyapp.aipy.agent_taskmgr:129 - Task 550e8400-e29b-41d4-a716-446655440000 completed
```

## Version Compatibility

- Requires AIPython 1.0.0+
- Compatible with FastAPI 0.68.0+
- Supports Python 3.8+
- Works with all supported LLM providers

## Future Enhancements

- WebSocket support for real-time updates
- Task scheduling and cron-like functionality
- Multi-tenant support with authentication
- Persistent task storage with database backend
- Distributed execution across multiple nodes
- Enhanced monitoring and metrics collection