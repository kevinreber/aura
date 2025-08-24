# Commute Intelligence System 🚗🚂

Complete traffic and transit intelligence for AI-powered morning routines.

## 🎯 Overview

The Daily MCP Server includes a comprehensive **Commute Intelligence System** that provides real-time traffic data, live transit schedules, and intelligent recommendations for your daily commute. This system integrates multiple data sources to give you the most accurate and personalized commute information possible.

## 🌟 Key Features

### 🚗 **Real-Time Traffic Data**

- **Google Maps API** integration for live traffic conditions
- **Door-to-door routing** with your exact home and work addresses
- **Real-time arrival predictions** based on current conditions
- **Route optimization** with alternative path suggestions

### 🚂 **Live Transit Schedules**

- **Official Caltrain GTFS data** with real train schedules
- **Live departure times** between any Caltrain stations
- **Real train numbers** and platform information
- **Automatic schedule updates** from official sources

### 🚌 **Complete Shuttle Integration**

- **MV Connector schedules** extracted from official timetables
- **All 3 stops**: Mountain View Caltrain ↔ LinkedIn Transit Center ↔ LinkedIn 950|1000
- **Real-time next departure** calculations
- **Service hours validation** (morning and evening schedules)

### 🤖 **AI-Powered Recommendations**

- **Smart comparisons**: "Drive 43min vs Transit 63min"
- **Context-aware suggestions** based on traffic and schedules
- **Personalized recommendations** using your address configuration
- **Time-sensitive advice** for optimal departure times

## 📋 Available Tools

### `mobility.get_commute_options`

**Comprehensive commute analysis with driving AND transit options.**

```json
{
  "direction": "to_work",
  "departure_time": "8:00 AM",
  "include_driving": true,
  "include_transit": true
}
```

**Response includes:**

- Real-time driving conditions with traffic
- Live Caltrain schedules with next departures
- MV Connector shuttle connections
- AI recommendation comparing all options

### `mobility.get_shuttle_schedule`

**Detailed MV Connector shuttle schedules between specific stops.**

```json
{
  "origin": "mountain_view_caltrain",
  "destination": "linkedin_transit_center",
  "departure_time": "9:00 AM"
}
```

**Response includes:**

- Next available shuttle departures
- Travel time between stops
- Service hours and frequency
- All stop information

### `mobility.get_commute` (Enhanced)

**Basic commute information with real-time traffic.**

```json
{
  "origin": "565 Del Monte Ave, South San Francisco, CA 94080",
  "destination": "1000 W Maude Ave, Sunnyvale, CA 94085",
  "mode": "driving"
}
```

## ⚙️ Configuration

### 🏠 Personal Address Setup

**Configure your real addresses for accurate routing:**

1. **Edit `.env` file:**

   ```bash
   HOME_ADDRESS=123 Your Street, Your City, State ZIP
   WORK_ADDRESS=456 Work Address, Work City, State ZIP

   # Optional Caltrain stations (defaults provided)
   HOME_CALTRAIN_STATION=South San Francisco
   WORK_CALTRAIN_STATION=Mountain View
   ```

2. **Address format best practices:**
   - ✅ Use complete addresses: `"565 Del Monte Ave, South San Francisco, CA 94080"`
   - ✅ Include apartment/suite numbers for precision
   - ❌ Avoid vague locations: `"South SF"` or company names

### 🗺️ Google Maps API Setup

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Create or select a project**
3. **Enable required APIs:**

   - Directions API (for routing and traffic)
   - Distance Matrix API (for batch calculations)

4. **Create API Key:**

   - Go to APIs & Services → Credentials
   - Create Credentials → API Key
   - Copy the key (looks like: `AIzaSyD...`)

5. **Secure your API key (Important!):**

   - Click the pencil icon next to your key
   - Set application restrictions (IP addresses or HTTP referrers)
   - Set API restrictions (select only the APIs you need)

6. **Add to `.env`:**
   ```bash
   GOOGLE_MAPS_API_KEY=your_actual_api_key_here
   ```

### 🚂 Caltrain GTFS Integration

**No additional setup required!** The system automatically:

- Downloads official GTFS data from Trillium Transit
- Caches schedules for 12 hours for performance
- Updates data daily to stay current
- Provides fallback to mock data if API unavailable

## 🧪 Testing Your Setup

### Quick Configuration Test

```bash
# Check if your addresses are configured
uv run python -c "
from mcp_server.config import get_settings; s = get_settings()
print(f'🏠 Home: {s.home_address or \"❌ Not set\"}')
print(f'🏢 Work: {s.work_address or \"❌ Not set\"}')
print(f'🗺️ Google Maps: {\"✅ Configured\" if s.google_maps_api_key else \"❌ Missing\"}')
"
```

### Test API Endpoints

**Morning commute analysis:**

```bash
curl -X POST http://localhost:8000/tools/mobility.get_commute_options \
  -H "Content-Type: application/json" \
  -d '{
    "direction": "to_work",
    "departure_time": "8:00 AM",
    "include_driving": true,
    "include_transit": true
  }'
```

**Shuttle schedule query:**

```bash
curl -X POST http://localhost:8000/tools/mobility.get_shuttle_schedule \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "mountain_view_caltrain",
    "destination": "linkedin_transit_center"
  }'
```

## 📊 Data Sources

### Real-Time Traffic

- **Provider**: Google Maps Directions API
- **Update Frequency**: Real-time
- **Cache Duration**: 15 minutes
- **Features**: Live traffic, route optimization, ETA predictions

### Caltrain Schedules

- **Provider**: Official GTFS feed from Trillium Transit
- **Update Frequency**: Daily automatic download
- **Cache Duration**: 12 hours
- **Features**: All routes, real train numbers, station details

### MV Connector Shuttles

- **Provider**: Official timetables (manually extracted)
- **Coverage**: Complete morning (6:50 AM - 10:58 AM) and evening (3:16 PM - 6:42 PM) schedules
- **Stops**: Mountain View Caltrain, LinkedIn Transit Center, LinkedIn 950|1000
- **Features**: Real-time next departure calculations, service validation

## 🎯 Use Cases

### Morning Routine AI Agent

**User**: _"How should I get to work?"_

**AI Response**: _"You have two good options:_

- _🚗 **Drive**: 43 minutes with light traffic via Del Monte Dr_
- _🚂 **Transit**: 63 minutes total - catch the 8:15 AM train from South SF, arrives MV at 9:02 AM, then 9:11 AM shuttle to LinkedIn_

_I recommend driving today since traffic is light and it's 20 minutes faster."_

### Dynamic Planning

**User**: _"I have a 9 AM meeting at work, when should I leave?"_

**AI Response**: _"For a 9 AM arrival:_

- _🚗 **Driving**: Leave by 8:05 AM (allows 12-minute buffer)_
- _🚂 **Transit**: Catch the 7:44 AM train (arrives 8:31 AM + 8min shuttle = 8:39 AM arrival)_

_Transit gets you there early with less stress - I'd recommend the 7:44 AM train."_

### Evening Flexibility

**User**: _"What's the best way home right now?"_

**AI Response**: _"Checking current conditions at 5:15 PM:_

- _🚗 **Driving**: 52 minutes due to heavy traffic on 101_
- _🚂 **Transit**: 58 minutes - next shuttle at 5:21 PM, catch 5:34 PM train_

_Transit is only 6 minutes longer and avoids traffic stress. Next shuttle leaves in 6 minutes!"_

## 🚀 Performance & Reliability

### Intelligent Caching

- **Traffic data**: 15-minute cache reduces API calls and costs
- **GTFS schedules**: 12-hour cache with daily updates
- **Shuttle data**: Static data with real-time calculations
- **Fallback systems**: Mock data when APIs unavailable

### Error Handling

- **Graceful degradation** when APIs are unavailable
- **Smart retries** for transient failures
- **Comprehensive logging** for troubleshooting
- **Mock data fallbacks** for continued functionality

### Rate Limiting Protection

- **Google Maps**: Cached routes prevent excessive API usage
- **GTFS Downloads**: Daily schedule updates, not per-request
- **Intelligent batching** for multiple queries

## 🔮 Future Enhancements

### Real-Time Transit Updates

- **511.org API integration** for live Caltrain delays
- **Service alert notifications** for disruptions
- **Dynamic route adjustments** based on delays

### Advanced Intelligence

- **Pattern learning** from your commute history
- **Weather-aware recommendations** (rain = prefer driving?)
- **Meeting-aware timing** (early departure for important meetings)
- **Alternative route suggestions** during incidents

### Expanded Coverage

- **Additional transit agencies** (BART, Muni, VTA)
- **More shuttle systems** beyond MV Connector
- **Multi-modal combinations** (bike + transit, park & ride)

## 💡 Tips for Best Results

### Address Configuration

- Use **complete addresses** including street numbers and ZIP codes
- Include **apartment/suite numbers** for maximum precision
- Test addresses in Google Maps first to ensure they're recognized

### API Key Management

- **Secure your API key** with IP/domain restrictions
- **Monitor usage** in Google Cloud Console
- **Set up billing alerts** if using high volumes

### Optimal Usage

- **Configure real addresses** for accurate door-to-door timing
- **Use appropriate departure times** (current time or future plans)
- **Include both driving and transit** for comprehensive comparisons
- **Trust the AI recommendations** - they consider real-time conditions

## 🎉 Ready for AI Agent Integration

Your commute intelligence system is now ready to power sophisticated AI agents that can:

- **Answer complex routing questions** with real-time data
- **Provide intelligent recommendations** based on current conditions
- **Coordinate multi-modal transportation** seamlessly
- **Adapt to your personal preferences** and address configuration
- **Handle both planned and spontaneous** travel requests

**Your daily AI assistant now has the intelligence of a local commute expert!** 🚀
