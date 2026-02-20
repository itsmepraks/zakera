# Conversation Export Documentation

## Overview

The conversation export feature enables users to export their conversation histories in multiple formats with real-time progress updates. This is useful for:

- **Data Portability**: Export conversations for backup or migration
- **Compliance**: Meet data retention and portability requirements (GDPR, etc.)
- **Analysis**: Export to CSV for data analysis and insights
- **Documentation**: Generate readable markdown or text logs
- **Archival**: Long-term storage of conversation histories

## Features

- ✅ **Streaming Export**: Efficient streaming for large conversations
- ✅ **Multiple Formats**: JSON, Markdown, Text, and CSV
- ✅ **Real-time Progress**: Live progress updates during export
- ✅ **Metadata Support**: Include tokens, costs, latency, and tool usage
- ✅ **Batch Processing**: Memory-efficient processing of large datasets
- ✅ **Authentication**: Secure access with JWT tokens
- ✅ **Authorization**: Users can only export their own conversations
- ✅ **Monitoring**: Full Prometheus metrics integration

## Supported Formats

### JSON Format
Structured export with full metadata support, ideal for programmatic access.

**Features:**
- Complete message history with timestamps
- Optional metadata (tokens, costs, latency, provider)
- Tool execution results
- Real-time progress updates
- Easy to parse and process

**Best for:** API integration, data processing, archival

### Markdown Format
Human-readable format with rich formatting support.

**Features:**
- Conversation title and metadata header
- Formatted messages with role indicators
- Timestamps and metadata inline
- Tool usage indicators
- Ready for documentation platforms

**Best for:** Documentation, sharing, human review

### Text Format
Plain text conversation log, simple and universal.

**Features:**
- Clean, readable format
- Timestamps on each message
- Role indicators (USER, ASSISTANT)
- No special formatting required
- Universal compatibility

**Best for:** Simple backups, email, text editors

### CSV Format
Tabular format for data analysis and reporting.

**Features:**
- One row per message
- Structured columns (id, timestamp, role, content, etc.)
- Optional metadata columns
- Excel/spreadsheet compatible
- Easy filtering and analysis

**Best for:** Data analysis, reporting, spreadsheets

## API Reference

### Endpoint

```
GET /api/v1/conversations/{conversation_id}/export
```

### Authentication

Requires JWT token in Authorization header:

```bash
Authorization: Bearer <your_jwt_token>
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | `json` | Export format: `json`, `markdown`, `text`, or `csv` |
| `include_metadata` | boolean | `true` | Include message metadata (tokens, costs, latency) |
| `include_tools` | boolean | `true` | Include tool execution results |
| `batch_size` | integer | `50` | Messages per batch (10-500) |

### Response Headers

```
Content-Type: application/json | text/markdown | text/plain | text/csv
Content-Disposition: attachment; filename="conversation_{id}.{format}"
X-Content-Type-Options: nosniff
Cache-Control: no-cache
```

### Response Status Codes

| Code | Description |
|------|-------------|
| 200 | Export successful |
| 401 | Unauthorized (invalid/missing token) |
| 404 | Conversation not found or access denied |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

## Usage Examples

### 1. Basic JSON Export

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/conversations/123/export" \
  > conversation.json
```

### 2. Markdown Export with Full Metadata

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/conversations/123/export?format=markdown&include_metadata=true" \
  > conversation.md
```

### 3. CSV Export for Analysis

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/conversations/123/export?format=csv" \
  > conversation.csv
```

### 4. Minimal Text Export

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/conversations/123/export?format=text&include_metadata=false" \
  > conversation.txt
```

### 5. Large Conversation with Custom Batch Size

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/conversations/123/export?batch_size=100" \
  > conversation.json
```

## JSON Export Protocol

The JSON export format returns a stream of newline-delimited JSON objects:

### 1. Metadata Object

```json
{
  "type": "metadata",
  "conversation_id": 123,
  "title": "AI Discussion",
  "created_at": "2026-02-19T10:30:00Z",
  "total_messages": 50
}
```

### 2. Progress Objects (Every 10 Messages)

```json
{
  "type": "progress",
  "processed": 20,
  "total": 50,
  "percentage": 40.0
}
```

### 3. Data Object

```json
{
  "type": "data",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "Hello!",
      "timestamp": "2026-02-19T10:30:15Z",
      "model": "gpt-4-turbo",
      "tokens": 5,
      "cost": 0.0001,
      "latency_ms": 250,
      "provider": "openai",
      "tools_used": []
    },
    ...
  ]
}
```

### 4. Complete Object

```json
{
  "type": "complete",
  "total_messages": 50
}
```

## Python Client Example

```python
import requests
import json

def export_conversation(conversation_id: int, token: str, format: str = "json"):
    """Export a conversation with progress tracking."""
    url = f"http://localhost:8000/api/v1/conversations/{conversation_id}/export"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"format": format, "include_metadata": True}
    
    response = requests.get(url, headers=headers, params=params, stream=True)
    response.raise_for_status()
    
    if format == "json":
        # Process streaming JSON
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                
                if data["type"] == "metadata":
                    print(f"Exporting: {data['title']}")
                    print(f"Total messages: {data['total_messages']}")
                
                elif data["type"] == "progress":
                    print(f"Progress: {data['percentage']:.1f}%")
                
                elif data["type"] == "data":
                    print(f"Received {len(data['messages'])} messages")
                    return data["messages"]
                
                elif data["type"] == "complete":
                    print(f"Export complete: {data['total_messages']} messages")
    else:
        # Save other formats directly
        with open(f"conversation_{conversation_id}.{format}", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Saved to conversation_{conversation_id}.{format}")

# Usage
token = "your_jwt_token"
messages = export_conversation(123, token, "json")
```

## JavaScript Client Example

```javascript
async function exportConversation(conversationId, token, format = 'json') {
  const url = `http://localhost:8000/api/v1/conversations/${conversationId}/export`;
  const params = new URLSearchParams({ format, include_metadata: true });
  
  const response = await fetch(`${url}?${params}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  if (!response.ok) {
    throw new Error(`Export failed: ${response.statusText}`);
  }
  
  if (format === 'json') {
    // Process streaming JSON
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line in buffer
      
      for (const line of lines) {
        if (line.trim()) {
          const data = JSON.parse(line);
          
          if (data.type === 'metadata') {
            console.log(`Exporting: ${data.title}`);
          } else if (data.type === 'progress') {
            console.log(`Progress: ${data.percentage}%`);
          } else if (data.type === 'data') {
            return data.messages;
          }
        }
      }
    }
  } else {
    // Download other formats
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation_${conversationId}.${format}`;
    a.click();
  }
}

// Usage
const token = 'your_jwt_token';
const messages = await exportConversation(123, token, 'json');
```

## Performance Considerations

### Batch Size

The `batch_size` parameter controls memory usage and streaming performance:

- **Small batches (10-20)**: More frequent progress updates, lower memory usage
- **Medium batches (50-100)**: Balanced performance (default: 50)
- **Large batches (200-500)**: Faster export, higher memory usage

**Recommendation:** Use default batch size unless you have specific requirements.

### Large Conversations

For conversations with 1000+ messages:

1. Use streaming to avoid loading all messages into memory
2. Increase batch size to 100-200 for faster processing
3. Monitor progress updates to track completion
4. Consider exporting during off-peak hours

### Network Considerations

- Exports are streamed to minimize memory usage
- Connection must remain open for entire export
- Use appropriate timeouts for large exports
- Consider compression for large JSON exports

## Error Handling

### Common Errors

#### 404 Not Found
```json
{
  "detail": "Conversation 123 not found or access denied"
}
```

**Causes:**
- Conversation doesn't exist
- User doesn't own the conversation
- Conversation was deleted

**Solution:** Verify conversation ID and ownership

#### 500 Internal Server Error
```json
{
  "detail": "Export failed. Please try again later."
}
```

**Causes:**
- Database connection error
- Unexpected data format
- System resource exhaustion

**Solution:** Check logs, retry after a moment

#### 429 Rate Limit Exceeded
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

**Causes:**
- Too many export requests in short time

**Solution:** Wait and retry with exponential backoff

### Retry Logic Example

```python
import time
from requests.exceptions import RequestException

def export_with_retry(conversation_id, token, max_retries=3):
    """Export with automatic retry on failure."""
    for attempt in range(max_retries):
        try:
            return export_conversation(conversation_id, token)
        except RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
            time.sleep(wait_time)
```

## Monitoring and Metrics

The export feature provides comprehensive Prometheus metrics:

### Export Request Metrics

```
# Total export requests by format and status
export_requests_total{format="json",status="success"} 150
export_requests_total{format="markdown",status="success"} 45
export_requests_total{format="csv",status="success"} 30
```

### Export Duration

```
# Export duration histogram by format
export_duration_seconds{format="json",quantile="0.5"} 2.5
export_duration_seconds{format="json",quantile="0.95"} 8.7
export_duration_seconds{format="json",quantile="0.99"} 15.3
```

### Messages Exported

```
# Total messages exported by format
export_messages_total{format="json"} 12500
export_messages_total{format="markdown"} 3200
```

### Export Errors

```
# Export errors by format and type
export_errors_total{format="json",error_type="not_found"} 5
export_errors_total{format="json",error_type="internal"} 2
```

### Grafana Dashboard Queries

```promql
# Export success rate
rate(export_requests_total{status="success"}[5m]) 
/ 
rate(export_requests_total[5m]) * 100

# Average export duration by format
rate(export_duration_seconds_sum[5m]) 
/ 
rate(export_duration_seconds_count[5m])

# Messages exported per minute
rate(export_messages_total[1m])
```

## Security Considerations

### Authentication
- All exports require valid JWT token
- Tokens should be kept secure and not shared
- Use HTTPS in production to encrypt tokens in transit

### Authorization
- Users can only export their own conversations
- Conversation ownership is validated before export
- Deleted conversations cannot be exported

### Data Protection
- Exported files may contain sensitive information
- Secure storage of exported files is user's responsibility
- Consider encrypting exports for sensitive data
- Implement retention policies for exported data

### Rate Limiting
- Export endpoints are rate-limited to prevent abuse
- Limits are per-user and configurable
- Excessive requests will receive 429 status codes

## Compliance and Legal

### GDPR Compliance
The export feature supports GDPR "Right to Data Portability":

- ✅ Machine-readable format (JSON, CSV)
- ✅ Structured data export
- ✅ Complete conversation history
- ✅ Metadata included
- ✅ Easy to transmit to another service

### Data Retention
- Exports provide point-in-time snapshots
- Original conversations remain in system
- Implement separate retention policies for exports
- Consider automated cleanup of old exports

## Troubleshooting

### Export Times Out

**Problem:** Large conversation export times out

**Solutions:**
1. Increase client timeout settings
2. Reduce batch size for more frequent streaming
3. Export during off-peak hours
4. Contact support for very large conversations (>10,000 messages)

### Incomplete Export

**Problem:** Export stops before completion

**Solutions:**
1. Check network connection stability
2. Verify sufficient disk space
3. Check server logs for errors
4. Retry the export

### Progress Updates Not Showing

**Problem:** No progress updates during JSON export

**Solutions:**
1. Ensure client is processing streaming response
2. Progress updates occur every 10 messages
3. Small conversations may complete before first update
4. Check client buffering settings

### Wrong Format Downloaded

**Problem:** File format doesn't match request

**Solutions:**
1. Verify `format` parameter in URL
2. Check `Content-Type` header in response
3. Clear browser/client cache
4. Use correct file extension when saving

## Best Practices

1. **Regular Backups**: Export important conversations regularly
2. **Format Selection**: Choose format based on use case
3. **Metadata Inclusion**: Include metadata for complete archives
4. **Secure Storage**: Store exports securely with encryption
5. **Retention Policy**: Implement cleanup of old exports
6. **Monitoring**: Track export metrics for performance insights
7. **Error Handling**: Implement retry logic for reliability
8. **Testing**: Test export functionality before relying on it

## Future Enhancements

Planned features for future releases:

- [ ] Scheduled automatic exports
- [ ] Email delivery of exports
- [ ] Cloud storage integration (S3, Google Drive, Dropbox)
- [ ] Compression options (gzip, zip)
- [ ] Partial exports (date range, message count)
- [ ] Export templates and customization
- [ ] Bulk export multiple conversations
- [ ] Export conversation branches separately
- [ ] Export to additional formats (PDF, HTML, XML)

## Support

For issues or questions about conversation export:

- Check this documentation
- Review API documentation at `/api/docs`
- Check Grafana metrics for system status
- Review application logs
- Contact support with conversation ID and error details

---

**Last Updated:** February 2026  
**Version:** 1.0.0  
**API Version:** v1
