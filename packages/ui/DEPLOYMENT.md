# 🚀 Daily Agent UI - Deployment Guide

## 📋 Prerequisites

Before deploying, ensure you have:

- ✅ AI Agent API deployed (Render/Railway/Vercel)
- ✅ MCP Server deployed (Render/Railway)
- ✅ All API endpoints working in production

**Current Production URLs (Render):**
- AI Agent: https://aura-agent-yz8u.onrender.com
- MCP Server: https://aura-server-sxxd.onrender.com

## 🌍 Environment Variables Setup

### 🎯 **Simple API URL Strategy**

The UI uses a straightforward environment variable approach:

1. **`VITE_AI_AGENT_API_URL`** - Set to your AI Agent API URL (dev or production)
2. **Localhost fallback** - Defaults to `http://localhost:8001` if not set

Simple and effective!

### 📱 **Local Development**

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Update your `.env` file:

```bash
# AI Agent API URL (local development)
VITE_AI_AGENT_API_URL=http://localhost:8001

# Environment identifier
VITE_ENVIRONMENT=development

# Optional: Enable debug mode
VITE_DEBUG=true
```

### 🚀 **Vercel Production**

1. **Deploy to Vercel:**

   ```bash
   npm run build
   npx vercel --prod
   ```

2. **Set Environment Variables** in Vercel Dashboard:
   - Go to: https://vercel.com/[username]/daily-agent-ui/settings/environment-variables
   - Add these variables:

   ```
   Name: VITE_AI_AGENT_API_URL
   Value: https://your-ai-agent-url.railway.app
   Environment: Production

   Name: VITE_ENVIRONMENT
   Value: production
   Environment: Production

   Name: VITE_DEBUG
   Value: false
   Environment: Production
   ```

3. **Redeploy** after setting environment variables:
   ```bash
   npx vercel --prod
   ```

## 🔗 **AI Agent API URLs**

Configure your environment variables based on where your AI Agent is deployed:

### **Render Deployment (Current Production):**

```
AI Agent: https://aura-agent-yz8u.onrender.com
MCP Server: https://aura-server-sxxd.onrender.com
```

Set your Vercel environment variable:
```
VITE_AI_AGENT_API_URL=https://aura-agent-yz8u.onrender.com
```

### **Railway Deployment:**

```
https://web-production-[hash].up.railway.app
```

### **Vercel Deployment:**

```
https://daily-ai-agent-[hash].vercel.app
```

## 🧪 **Testing Production Setup**

1. **Local Testing with Production API:**

   ```bash
   # Update .env temporarily
   VITE_AI_AGENT_API_URL=https://your-production-ai-agent-url
   npm run dev
   ```

2. **Check Console Logs:**
   - Open browser DevTools
   - Look for: `🔗 AI Agent API URL: [url]`
   - Verify API calls work

3. **Production Testing:**
   ```bash
   npm run build
   npm run preview
   ```

## 🚨 **Common Issues**

### **CORS Errors**

If you see CORS errors, ensure your AI Agent API includes the UI domain in allowed origins:

```python
# In your AI Agent API (daily_ai_agent/models/config.py)
allowed_origins: List[str] = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://daily-agent-ui.vercel.app",  # Add your Vercel domain
    "https://your-custom-domain.com"      # Add any custom domains
]
```

### **Environment Variables Not Loading**

- Variables must be prefixed with `VITE_` for client-side access
- Restart dev server after changing `.env` files
- Check browser console for debug messages

### **API Connection Issues**

- Verify AI Agent API is running and accessible
- Test API endpoints directly: `curl https://your-api-url/health`
- Check network tab in browser DevTools

## 📦 **Deployment Checklist**

- [ ] AI Agent API deployed and accessible
- [ ] MCP Server deployed and accessible
- [ ] Environment variables set in Vercel
- [ ] CORS origins updated in AI Agent API
- [ ] UI builds successfully (`npm run build`)
- [ ] Production deployment tested
- [ ] All widgets load data correctly
- [ ] AI chat functionality works

## 🛠 **Development Commands**

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run typecheck
```

## 🔄 **Continuous Deployment**

For automatic deployments, connect your GitHub repository to Vercel:

1. Go to: https://vercel.com/new
2. Import your repository
3. Set environment variables
4. Deploy automatically on every push to `main`

---

🎉 **Your Daily Agent UI will be ready for production!**
