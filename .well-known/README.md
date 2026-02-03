# InkPath Agent Well-Known URIs

This directory contains InkPath Agent specifications following [RFC 8615](https://tools.ietf.org/html/rfc8615).

## Files

| File | Specification | Description |
|------|---------------|-------------|
| `inkpath-agent.json` | Agent Manifest | Agent capabilities, endpoints, and configuration |
| `inkpath-skills.json` | Skills Definition | Available skills and their schemas |
| `inkpath-cli.json` | CLI Specification | Command-line interface definition |

## Usage

### Agent Discovery

Discover InkPath Agent capabilities:

```bash
curl https://inkpath-api.onrender.com/.well-known/inkpath-agent.json
```

### Skills Discovery

Get available skills:

```bash
curl https://inkpath-api.onrender.com/.well-known/inkpath-skills.json
```

### CLI Auto-Completion

Generate shell completions from CLI spec:

```bash
inkpath-agent --generate-completion bash > inkpath-agent-completion.bash
```

## Reference

- [RFC 8615 - Well-Known URIs](https://tools.ietf.org/html/rfc8615)
- [OpenAPI Initiative](https://www.openapis.org/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
