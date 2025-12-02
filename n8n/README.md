# Odin n8n Workflows

This directory contains n8n workflow definitions for automating tasks using the Odin MCP API.

## Workflows

### notebookllm-automation.json

Automates the full NotebookLLM content generation pipeline:

1. **Add Source** - Adds a URL to NotebookLLM as a source
2. **Generate Content** - Generates infographic and presentation in parallel
3. **Download Content** - Downloads the generated infographic and presentation
4. **Convert to Images** - Converts the presentation PDF to PNG images

#### Configuration

Update the `Set Parameters` node with your settings:

- `source_url`: The URL of the webpage to add as a source
- `output_dir`: Directory to save downloaded files (default: `/tmp/notebookllm`)
- `mcp_endpoint`: Odin MCP API endpoint (default: `https://odin.api.ibytechaos.com/mcp`)

#### MCP API Format

All requests use JSON-RPC 2.0 format:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      "param1": "value1"
    }
  }
}
```

#### Available Tools

| Tool | Description |
|------|-------------|
| `notebookllm_add_source` | Add a web source (URL) to a notebook |
| `notebookllm_generate_infographic` | Generate an infographic from sources |
| `notebookllm_generate_presentation` | Generate a presentation from sources |
| `notebookllm_download_content` | Download generated content |
| `pdf_to_images` | Convert PDF to images |

## Import to n8n

1. Open n8n
2. Go to Workflows
3. Click Import from File
4. Select the JSON workflow file

## Requirements

- Odin MCP server running at the configured endpoint
- Chrome browser with remote debugging enabled (for NotebookLLM automation)
- Google account logged in to NotebookLLM
