# OAuth Implicit Grant Authentication Guide

## Overview
The REST client now supports OAuth 2.0 implicit grant flow as an alternative to cookie-based session authentication. This avoids the fallback to form-post login and provides better support for SSO-only institutions.

## Authentication Priority Order
1. **Explicit Token Auth** (highest priority) - `EBI_REST_ACCESS_TOKEN` or `EBI_REST_ADMIN_TOKEN`
2. **OAuth Implicit Grant** - `EBI_OAUTH_CLIENT_ID` (and optional `EBI_OAUTH_REDIRECT_URI`)
3. **Cookie Session** (fallback) - Form-post login to various known endpoints

## Setup Requirements

### 1. Register OAuth Client in openEQUELLA
First, you need to register an OAuth client application in openEQUELLA:

1. Go to Settings → Integration → OAuth
2. Click "Register new client application"
3. Configure:
   - **Descriptive name**: e.g., "EBI Importer"
   - **OAuth flow**: Select "Implicit Grant"
   - **Redirect URL**: 
     - For embedded browser: Select "My application doesn't host a redirect URL, I want to use the default"
     - For custom web redirect: Select "I want to use a custom redirect URL" and enter your URL
   - **Token validity**: Set appropriate duration (e.g., 30 days)
4. Save and note the **Client ID**

### 2. Set Environment Variables

#### Option A: Using Default Redirect (Recommended for Python CLI)
```bash
export EBI_OAUTH_CLIENT_ID="your-client-id-here"
# EBI_OAUTH_REDIRECT_URI not needed - will use default
```

#### Option B: Using Custom Redirect URI
```bash
export EBI_OAUTH_CLIENT_ID="your-client-id-here"
export EBI_OAUTH_REDIRECT_URI="http://your-domain.com/oauth/callback"
```

## How It Works

### With Default Redirect (Automatic Token Capture)
1. Client opens browser to OAuth authorization endpoint
2. User logs in to openEQUELLA
3. User approves access
4. openEQUELLA redirects to default page with token in URL fragment
5. Client's local HTTP server captures the token
6. Browser window can be closed
7. Client uses token for all subsequent API calls

### With Custom Redirect URI (Manual Token Extraction)
1. Client opens browser to OAuth authorization endpoint
2. User logs in to openEQUELLA
3. User approves access
4. openEQUELLA redirects to your custom URL with token in fragment: `https://your-domain.com/callback#access_token=YOUR_TOKEN_HERE`
5. User is prompted to paste the token
6. Client uses token for all subsequent API calls

## Implementation Details

The client now supports three methods:

### `_establish_implicit_grant_session()`
Main method that orchestrates the implicit grant flow. Automatically chooses between local server capture or manual token entry based on whether a custom redirect URI is configured.

### `_capture_implicit_grant_token_via_server(port=9999)`
When using default redirect, this method:
- Starts a local HTTP server on localhost:9999
- Opens browser to OAuth endpoint
- Waits for redirect with token (5 minute timeout)
- Extracts token from URL fragment
- Returns the token

### `_prompt_for_implicit_grant_token()`
When using custom redirect URI:
- Opens browser to OAuth endpoint
- Prompts user to copy token from browser URL
- User pastes token at command prompt
- Returns the token

## Environment Variables Summary

| Variable | Required | Description |
|----------|----------|-------------|
| `EBI_OAUTH_CLIENT_ID` | Yes (for implicit grant) | OAuth client ID from openEQUELLA settings |
| `EBI_OAUTH_REDIRECT_URI` | No | Custom redirect URL; if omitted uses "default" with local server |
| `EBI_REST_ACCESS_TOKEN` | No | Explicit access token (bypasses OAuth flow) |
| `EBI_REST_ADMIN_TOKEN` | No | Explicit admin token (bypasses OAuth flow) |

## Examples

### Python Import with Implicit Grant (Default)
```bash
export EBI_OAUTH_CLIENT_ID="abc123def456"
python import_script.py
# Browser opens automatically, user logs in, token captured automatically
```

### Using Explicit Token (No Browser Needed)
```bash
export EBI_REST_ACCESS_TOKEN="your-token-uuid-here"
python import_script.py
# No browser interaction, direct API access
```

### Fallback Behavior
If OAuth setup fails or client_id is not set, the system automatically falls back to cookie-based session authentication (form-post login).

## Troubleshooting

### "OAuth implicit grant failed: ... Falling back to cookie session"
- Verify `EBI_OAUTH_CLIENT_ID` is set correctly
- Verify the client is configured in openEQUELLA with "Implicit Grant" flow
- Check that your institution URL is correct

### Browser doesn't open automatically
- The webbrowser module may not work on headless systems
- Set `EBI_OAUTH_REDIRECT_URI` to your custom callback URL
- You'll be prompted to manually paste the token

### Token not captured after opening browser
- Ensure port 9999 is not in use (or modify the port in the code)
- Check firewall settings if on a corporate network
- Use 5-minute timeout to abandon and retry

### Connection refused or timeout
- Verify institution URL is correct and accessible
- Check network/proxy settings
- Try with explicit token instead: `export EBI_REST_ACCESS_TOKEN="..."`

## Advantages Over Cookie Session

✅ **No credential storage** - Token is temporary and limited-scope  
✅ **Better SSO support** - Works with SSO-only institutions  
✅ **Faster authentication** - No form submission roundtrips  
✅ **Token revocation** - Tokens can be revoked in openEQUELLA settings  
✅ **Audit trail** - Token usage is logged in openEQUELLA  
✅ **Browser-friendly** - User sees standard OAuth login dialog  

## Token Management

Once obtained, tokens can be:
- **Revoked** via openEQUELLA OAuth settings (Generated tokens section)
- **Viewed** in openEQUELLA OAuth settings to track active tokens
- **Reused** across multiple invocations by setting `EBI_REST_ACCESS_TOKEN`

## Security Notes

- Tokens are sent in HTTP headers (`X-Authorization: access_token=...`)
- Always use HTTPS in production
- Treat tokens like passwords - don't commit to version control
- Use token revocation in openEQUELLA if credentials are compromised
