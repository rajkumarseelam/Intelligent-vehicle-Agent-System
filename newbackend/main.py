"""
Agentic AI In-Vehicle Assistant - Main FastAPI Application
Complete backend with multi-agent system, Groq AI integration, and perfect frontend sync
Maintains exact API contracts for seamless frontend-backend integration
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import tempfile

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import our modules
from agents import AgentOrchestrator, AgentMessage, MemoryManager
from tools import get_complete_vehicle_state
from intent_disambiguation import classify_intent

# Ensure directories exist FIRST
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Configure logging AFTER directory creation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/assistant.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ====================== PYDANTIC MODELS ======================

class VoiceRequest(BaseModel):
    text: str
    user_id: str = "default_user"
    user_location: Optional[Dict] = None
    
    class Config:
        schema_extra = {
            "example": {
                "text": "Find restaurants near me",
                "user_id": "john_doe", 
                "user_location": {
                    "latitude": 13.0827,
                    "longitude": 80.2707,
                    "is_fallback": False
                }
            }
        }

class VehicleCommand(BaseModel):
    command: str
    parameters: Dict = {}
    user_id: str = "default_user"

class AgentResponse(BaseModel):
    response: str
    agent_used: str
    actions_taken: List[str]
    vehicle_state: Dict

class UserRegistration(BaseModel):
    username: str
    email: str
    password: str
    vehicleType: str
    vehicleModel: str
    billId: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict] = None

# ====================== FASTAPI APPLICATION ======================

app = FastAPI(
    title="Agentic AI In-Vehicle Assistant",
    description="Multi-agent AI system with Groq AI integration for personalized vehicle control",
    version="3.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================== GLOBAL VARIABLES ======================

agent_orchestrator: Optional[AgentOrchestrator] = None
memory_manager: Optional[MemoryManager] = None
active_connections: List[WebSocket] = []

# ====================== STARTUP/SHUTDOWN ======================

@app.on_event("startup")
async def startup_event():
    """Initialize all components on startup"""
    global agent_orchestrator, memory_manager
    
    logger.info("🚀 Starting Agentic AI In-Vehicle Assistant v3.0...")
    
    # Log API configuration
    google_key = os.getenv("GOOGLE_MAPS_API_KEY")
    weather_key = os.getenv("OPENWEATHER_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    
    logger.info(f"🗺️ Google Maps API: {'✅ Configured' if google_key else '❌ Not configured'}")
    logger.info(f"🌤️ OpenWeather API: {'✅ Configured' if weather_key else '❌ Not configured'}")
    logger.info(f"🤖 Groq AI API: {'✅ Configured' if groq_key else '❌ Not configured'}")
    
    try:
        # Initialize agent orchestrator (includes memory manager)
        agent_orchestrator = AgentOrchestrator()
        await agent_orchestrator.initialize()
        
        # Get memory manager reference
        memory_manager = agent_orchestrator.get_memory_manager()
        
        logger.info("✅ All systems initialized successfully!")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise e

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🔄 Shutting down...")
    # Add any cleanup logic here

# ====================== HELPER FUNCTIONS ======================

async def verify_user_authenticated(user_id: str) -> bool:
    """Verify user is authenticated"""
    if not memory_manager:
        return False
    return await memory_manager.is_user_authenticated(user_id)

def check_auth_and_logout(response_status: int) -> bool:
    """Check if response indicates auth failure"""
    return response_status == 401

# ====================== WEBSOCKET ENDPOINT ======================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for real-time communication"""
    await websocket.accept()
    active_connections.append(websocket)
    logger.info("🔌 New WebSocket connection established")
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Create agent message
            user_message = AgentMessage(
                content=message_data.get("text", ""),
                user_id=message_data.get("user_id", "default_user"),
                timestamp=datetime.now(),
                message_type="user_input",
                user_location=message_data.get("user_location")
            )
            
            # Process through agent orchestrator
            response = await agent_orchestrator.process_message(user_message)
            
            # Send response back
            await websocket.send_text(json.dumps({
                "response": response.content,
                "agent_used": response.agent_id,
                "actions_taken": response.actions_taken,
                "vehicle_state": response.vehicle_state,
                "timestamp": response.timestamp.isoformat()
            }))
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("🔌 WebSocket connection closed")

# ====================== AUTHENTICATION ENDPOINTS ======================

@app.post("/api/auth/register", response_model=AuthResponse)
async def register_user(user_data: UserRegistration):
    """Register a new user"""
    try:
        if not memory_manager:
            raise HTTPException(status_code=500, detail="Memory manager not initialized")
        
        # Map vehicle models to proper data
        vehicle_data_mapping = {
            "tesla_model_3": {"id": "tesla_model_3", "name": "Tesla Model 3"},
            "bmw_3_series": {"id": "bmw_3_series", "name": "BMW 3 Series"},
            "honda_civic": {"id": "honda_civic", "name": "Honda Civic"},
            "ford_f_150": {"id": "ford_f_150", "name": "Ford F-150"},
            "ram_1500": {"id": "ram_1500", "name": "RAM 1500"},
            "toyota_tacoma": {"id": "toyota_tacoma", "name": "Toyota Tacoma"}
        }
        
        vehicle_data = vehicle_data_mapping.get(user_data.vehicleModel, {
            "id": user_data.vehicleModel,
            "name": user_data.vehicleModel.replace('_', ' ').title()
        })
        
        # Register user
        success, message, user_response = await memory_manager.register_user(
            username=user_data.username.strip(),
            email=user_data.email.strip(),
            password=user_data.password,
            vehicle_type=user_data.vehicleType,
            vehicle_model=user_data.vehicleModel,
            vehicle_data=vehicle_data
        )
        
        return AuthResponse(
            success=success,
            message=message,
            user=user_response
        )
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return AuthResponse(
            success=False,
            message="Registration failed due to server error."
        )

@app.post("/api/auth/login", response_model=AuthResponse)
async def login_user(login_data: UserLogin):
    """Authenticate user login"""
    try:
        if not memory_manager:
            raise HTTPException(status_code=500, detail="Memory manager not initialized")
        
        # Authenticate user
        success, message, user_response = await memory_manager.authenticate_user(
            username=login_data.username.strip(),
            password=login_data.password
        )
        
        return AuthResponse(
            success=success,
            message=message,
            user=user_response
        )
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return AuthResponse(
            success=False,
            message="Login failed due to server error."
        )

# ====================== VOICE AND ASSISTANT API ======================

@app.post("/api/voice/process", response_model=AgentResponse)
async def process_voice_input(request: VoiceRequest):
    """Process text/voice input through multi-agent system"""
    try:
        # Authentication check
        if not await verify_user_authenticated(request.user_id):
            raise HTTPException(
                status_code=401, 
                detail=f"User '{request.user_id}' is not registered. Please register or login first."
            )
        
        logger.info(f"🎤 Processing input from {request.user_id}: '{request.text}'")
        
        # Create agent message with location data
        user_message = AgentMessage(
            content=request.text,
            user_id=request.user_id,
            timestamp=datetime.now(),
            message_type="text_input",
            user_location=request.user_location
        )
        
        # 🔧 DEBUG: Add intent classification debugging
        intent_result = classify_intent(request.text)
        logger.info(f"🔍 INTENT DEBUG for '{request.text}': {intent_result}")
        
        # Process through agent orchestrator
        response = await agent_orchestrator.process_message(user_message)
        
        logger.info(f"🎯 Response from {response.agent_id}: {response.content[:100]}...")
        
        return AgentResponse(
            response=response.content,
            agent_used=response.agent_id,
            actions_taken=response.actions_taken,
            vehicle_state=response.vehicle_state
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice/upload")
async def upload_audio(file: UploadFile = File(...), user_id: str = "default_user"):
    """Process uploaded audio file"""
    try:
        # Authentication check
        if not await verify_user_authenticated(user_id):
            raise HTTPException(
                status_code=401, 
                detail=f"User '{user_id}' is not registered. Please register or login first."
            )
        
        # For now, return a mock response since we don't have speech recognition
        # In a real implementation, you'd use speech-to-text here
        return {
            "response": "Audio upload received. Speech recognition not yet implemented in this version.",
            "agent_used": "system",
            "actions_taken": ["audio_received"],
            "vehicle_state": get_complete_vehicle_state()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ====================== VEHICLE CONTROL ENDPOINTS ======================

@app.get("/api/vehicle/status")
async def get_vehicle_status(user_id: str):
    """Get current vehicle status"""
    try:
        # Authentication check
        if not await verify_user_authenticated(user_id):
            raise HTTPException(
                status_code=401, 
                detail=f"User '{user_id}' is not registered. Please register or login first."
            )
        
        # Get vehicle status from orchestrator
        status = await agent_orchestrator.get_vehicle_status(user_id)
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vehicle status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vehicle/command")
async def execute_vehicle_command(command: VehicleCommand):
    """Execute vehicle command"""
    try:
        # Authentication check
        if not await verify_user_authenticated(command.user_id):
            raise HTTPException(
                status_code=401, 
                detail=f"User '{command.user_id}' is not registered. Please register or login first."
            )
        
        # Create agent message for vehicle command
        message = AgentMessage(
            content=f"Execute {command.command} with parameters {command.parameters}",
            user_id=command.user_id,
            timestamp=datetime.now(),
            message_type="vehicle_command"
        )
        
        # Process through agent orchestrator
        response = await agent_orchestrator.process_message(message)
        
        return {
            "success": True,
            "message": response.content,
            "vehicle_state": response.vehicle_state,
            "actions_taken": response.actions_taken
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vehicle command error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ====================== MEMORY AND HISTORY ENDPOINTS ======================

@app.get("/api/memory/{user_id}")
async def get_user_memory(user_id: str):
    """Get user memory and interaction history"""
    try:
        # Authentication check
        if not await verify_user_authenticated(user_id):
            raise HTTPException(
                status_code=401, 
                detail=f"User '{user_id}' is not registered. Please register or login first."
            )
        
        if not memory_manager:
            raise HTTPException(status_code=500, detail="Memory manager not available")
        
        memory_data = await memory_manager.get_user_memory(user_id)
        return memory_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ====================== UTILITY ENDPOINTS ======================

@app.get("/api/weather/current")
async def get_current_weather(lat: float = 13.0827, lon: float = 80.2707):
    """Get current weather information"""
    try:
        from tools import NavigationTools
        weather_info = await NavigationTools.get_weather(latitude=lat, longitude=lon)
        return weather_info
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return {"error": "Weather service unavailable", "message": str(e)}

@app.get("/api/maps/test")
async def test_maps():
    """Test Google Maps integration"""
    try:
        from tools import NavigationTools
        result = await NavigationTools.search_nearby_places(
            place_type="restaurant",
            latitude=13.0827,
            longitude=80.2707
        )
        return {"status": "success", "sample_result": result}
    except Exception as e:
        logger.error(f"Maps test error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/maps/directions")
async def test_directions(origin: str = "Chennai", destination: str = "Bangalore"):
    """Test directions endpoint"""
    try:
        from tools import NavigationTools
        result = await NavigationTools.get_directions(destination, latitude=13.0827, longitude=80.2707)
        return result
    except Exception as e:
        logger.error(f"Directions test error: {e}")
        return {"error": "Directions service unavailable", "message": str(e)}

@app.post("/api/test/intent")
async def test_intent_classification(text: str):
    """Test intent classification"""
    try:
        intent_result = classify_intent(text)
        return {
            "text": text,
            "intent_classification": intent_result,
            "groq_fallback": intent_result.get('confidence', 0) < 0.3
        }
    except Exception as e:
        logger.error(f"Intent test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ====================== HEALTH CHECK ENDPOINT ======================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "agent_orchestrator": agent_orchestrator is not None,
            "memory_manager": memory_manager is not None,
        },
        "active_connections": len(active_connections),
        "version": "3.0.0",
        "features": {
            "authentication": True,
            "multi_agent_system": True,
            "groq_ai_integration": bool(os.getenv("GROQ_API_KEY")),
            "google_maps_integration": bool(os.getenv("GOOGLE_MAPS_API_KEY")),
            "weather_integration": bool(os.getenv("OPENWEATHER_API_KEY")),
            "voice_processing": True,
            "websocket_support": True,
            "vehicle_state_sync": True
        },
        "api_status": {
            "google_maps": "✅ Active" if os.getenv("GOOGLE_MAPS_API_KEY") else "⚠️ Using fallback",
            "weather": "✅ Active" if os.getenv("OPENWEATHER_API_KEY") else "⚠️ Using mock data",
            "groq_ai": "✅ Active" if os.getenv("GROQ_API_KEY") else "⚠️ Limited general conversation"
        }
    }

# ====================== ROOT ENDPOINT ======================

@app.get("/")
async def root():
    """Welcome message with API status"""
    google_configured = bool(os.getenv("GOOGLE_MAPS_API_KEY"))
    weather_configured = bool(os.getenv("OPENWEATHER_API_KEY"))
    groq_configured = bool(os.getenv("GROQ_API_KEY"))
    
    features = [
        "🔐 Secure User Authentication",
        "🤖 Multi-Agent AI System (7 specialized agents)",
        "🧠 Groq AI Integration for General Conversation",
        "🎵 Music Control & Entertainment",
        "🌡️ Climate Control & HVAC",
        "🚗 Vehicle Systems (doors, lights, etc.)",
        f"🗺️ {'Google Maps' if google_configured else 'OpenStreetMap'} Navigation",
        f"🌤️ {'Real Weather Data' if weather_configured else 'Mock Weather'} Integration",
        "📊 Comprehensive Vehicle Information Database",
        "👤 User Personalization & Memory",
        "📍 Real-time Location Services",
        "🔌 WebSocket Real-time Communication"
    ]
    
    return {
        "message": "🚗 Agentic AI In-Vehicle Assistant v3.0",
        "description": "Multi-agent AI system with Groq AI integration for intelligent vehicle control",
        "features": features,
        "api_status": {
            "google_maps": "✅ Active" if google_configured else "⚠️ Using OpenStreetMap fallback",
            "weather": "✅ Active" if weather_configured else "⚠️ Using mock data",
            "groq_ai": "✅ Active" if groq_configured else "⚠️ Limited general conversation",
            "multi_agent_system": "✅ Active (7 specialized agents)",
            "authentication": "✅ Active (SQLite database)"
        },
        "endpoints": {
            "register": "/api/auth/register",
            "login": "/api/auth/login",
            "voice_input": "/api/voice/process",
            "audio_upload": "/api/voice/upload",
            "vehicle_status": "/api/vehicle/status",
            "vehicle_command": "/api/vehicle/command",
            "user_memory": "/api/memory/{user_id}",
            "weather": "/api/weather/current",
            "maps_test": "/api/maps/test",
            "directions_test": "/api/maps/directions",
            "intent_test": "/api/test/intent",
            "websocket": "/ws",
            "health": "/health"
        },
        "setup_guide": {
            "required_env_vars": [
                "GROQ_API_KEY - For general conversation AI",
                "GOOGLE_MAPS_API_KEY - For enhanced navigation (optional)",
                "OPENWEATHER_API_KEY - For real weather data (optional)"
            ],
            "env_file_example": "Create .env file with your API keys"
        },
        "agent_system": {
            "master_agent": "Coordinates all agents and handles Groq AI fallback",
            "climate_agent": "Temperature, AC, and HVAC control",
            "entertainment_agent": "Music playback and audio control",
            "vehicle_control_agent": "Doors, lights, and vehicle systems",
            "navigation_agent": "GPS, directions, weather, and place search",
            "vehicle_info_agent": "Vehicle database and specifications",
            "user_experience_agent": "Personalization and general assistance"
        }
    }

# ====================== MAIN EXECUTION ======================

if __name__ == "__main__":
    # Log startup configuration
    print("\n" + "="*60)
    print("🚗 AGENTIC AI VEHICLE ASSISTANT v3.0")
    print("="*60)
    print(f"🤖 Groq AI: {'✅ Configured' if os.getenv('GROQ_API_KEY') else '❌ Not configured'}")
    print(f"🗺️ Google Maps: {'✅ Configured' if os.getenv('GOOGLE_MAPS_API_KEY') else '❌ Not configured'}")
    print(f"🌤️ Weather API: {'✅ Configured' if os.getenv('OPENWEATHER_API_KEY') else '❌ Not configured'}")
    print(f"🔐 Authentication: ✅ Enabled (SQLite)")
    print(f"🤖 Multi-Agent System: ✅ Active (7 agents)")
    print(f"🔌 WebSocket Support: ✅ Active")
    print(f"🎯 Intent Classification: ✅ Active")
    print("="*60)
    print(f"🌐 Starting server on http://localhost:8000")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("="*60 + "\n")
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )