# UI Production Deployment Guide

## 🚀 **Vercel Production Setup**

Your UI is deployed at: `https://daily-agent-ui.vercel.app`

## **Environment Variables for Vercel**

Set these environment variables in your Vercel project dashboard:

### **AI Agent Connection**
```bash
VITE_AI_AGENT_API_URL=https://web-production-f80730.up.railway.app
```

### **Optional Debug Configuration**
```bash
VITE_DEBUG=false
VITE_ENVIRONMENT=production
```

## ✅ **What's Already Configured**

Your UI configuration already includes:

- **✅ Dynamic API URL**: Uses `VITE_AI_AGENT_API_URL` environment variable
- **✅ Local Fallback**: Defaults to `http://localhost:8001` for development
- **✅ Error Handling**: Graceful fallbacks to mock data
- **✅ Server-Side Support**: Both client and server-side API clients
- **✅ Proxy API Routes**: Server-side routes to eliminate CORS issues

## 🔄 **Deployment Flow**

1. **Update Vercel Environment Variables**:
   ```bash
   VITE_AI_AGENT_API_URL=https://web-production-f80730.up.railway.app
   ```

2. **Redeploy UI** - Vercel will automatically redeploy with new env vars

3. **Test Full Integration**:
   - UI loads dashboard data from production AI agent
   - AI chat connects to production AI agent
   - AI agent fetches real data from production MCP server
   - MCP server provides real Google Calendar data

## 🧪 **Testing Production Integration**

Visit your UI at: `https://daily-agent-ui.vercel.app`

Test these features:
- **✅ Weather Widget** - Real weather data
- **✅ Financial Widget** - Real stock/crypto prices  
- **✅ Calendar Widget** - Real Google Calendar events (Runna, Family, Personal)
- **✅ AI Chat** - Real conversational AI with tools
- **✅ Slash Commands** - `/calendar`, `/finance`, etc.

## 🔗 **Full Production Architecture**

```
UI (Vercel)
├── https://daily-agent-ui.vercel.app
│
├── AI Agent (Railway)  
│   ├── https://web-production-f80730.up.railway.app
│   │
│   └── MCP Server (Railway)
│       ├── https://web-production-66f9.up.railway.app
│       │
│       └── External APIs
│           ├── Google Calendar API
│           ├── OpenWeatherMap API
│           ├── Alpha Vantage API (stocks)
│           └── CoinGecko API (crypto)
```

## 🎯 **Expected Results After Deployment**

- **🏃‍♂️ Real Training Schedule**: Runna workouts in calendar widget
- **📅 Real Events**: Personal calendar events (📞 boop time, etc.)
- **💰 Live Market Data**: Current stock and crypto prices
- **🌤️ Current Weather**: Real San Francisco weather
- **🤖 Smart AI**: Real conversations with access to all your data

## 🛠️ **Vercel Environment Variable Setup**

1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Add: `VITE_AI_AGENT_API_URL` = `https://web-production-f80730.up.railway.app`
3. Deploy: Vercel will automatically trigger a new deployment

## 🔒 **Security Notes**

- ✅ No API keys in frontend code
- ✅ All sensitive operations happen server-side
- ✅ CORS properly configured across all services
- ✅ Environment variables secure in Vercel dashboard
