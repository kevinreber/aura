# AI Agent Production Deployment Guide

## 🚀 **Railway Production Setup**

Your AI agent is ready for production deployment! Here's how to configure it:

### **Current Production URL**: `https://web-production-f80730.up.railway.app`

## **Environment Variables for Railway**

Set these environment variables in your Railway AI Agent project dashboard:

### **Core Configuration**

```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false
```

### **AI Model Configuration**

```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
DEFAULT_LLM=openai
```

### **MCP Server Connection**

```bash
MCP_SERVER_URL=https://web-production-66f9.up.railway.app
MCP_SERVER_TIMEOUT=45
```

### **Web Server Configuration**

```bash
HOST=0.0.0.0
# Railway automatically sets PORT - no need to configure manually
# PORT=8001  # Railway will override this
```

### **Security & CORS**

```bash
RATE_LIMIT_PER_MINUTE=100
# ALLOWED_ORIGINS is hardcoded in config for production URLs
```

### **User Preferences** (Optional)

```bash
USER_NAME=Kevin
USER_LOCATION=San Francisco
DEFAULT_COMMUTE_ORIGIN=Home
DEFAULT_COMMUTE_DESTINATION=Office
```

## ✅ **What's Already Configured**

Your AI agent config already includes:

- **✅ Dynamic Port**: Uses Railway's `PORT` environment variable
- **✅ Production CORS**: Includes all production URLs
- **✅ MCP Server Integration**: Ready to connect to production MCP server
- **✅ Error Handling**: Validates required API keys in production
- **✅ Smart Defaults**: Falls back to localhost for development

## 🔄 **Deployment Flow**

1. **Add Environment Variables** to Railway AI Agent project
2. **Deploy Automatically** - Railway detects changes
3. **Update MCP Server URL** - Point to production MCP server
4. **Test Integration** - Verify AI agent connects to production MCP

## 🧪 **Testing Production Deployment**

```bash
# Test health endpoint
curl https://web-production-f80730.up.railway.app/health

# Test chat endpoint
curl -X POST https://web-production-f80730.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, what can you help me with?"}'

# Test tools integration
curl https://web-production-f80730.up.railway.app/tools
```

## 🔗 **Service Integration**

- **MCP Server**: `https://web-production-66f9.up.railway.app`
- **AI Agent**: `https://web-production-f80730.up.railway.app`
- **UI**: `https://daily-agent-ui.vercel.app`

## 🛠️ **Next Steps After Deployment**

1. **Update UI Environment Variables** - Point to production AI agent
2. **Test Full Flow** - UI → AI Agent → MCP Server → Google Calendar
3. **Monitor Logs** - Check Railway logs for any issues

## 🔒 **Security Notes**

- ✅ No sensitive data in code repository
- ✅ All secrets stored in Railway environment variables
- ✅ CORS properly configured for production domains
- ✅ Rate limiting enabled for production use
