"""
Vehicle Control & Navigation Tools for AI Assistant
All vehicle functions, navigation, and utility methods
Maintains exact frontend-backend integration contracts
"""

import asyncio
import json
import logging
import os
import random
import re
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
import pygame

logger = logging.getLogger(__name__)

# Global music pause state tracking
MUSIC_PAUSED_STATE = {
    "is_paused": False,
    "current_file": None,
    "position": 0  # We can't actually track position with pygame.mixer.music, but we can track state
}

# Global vehicle state - matches frontend expectations exactly
VEHICLE_STATE = {
    "climate": {
        "temperature": 22,
        "fan_speed": 2,
        "ac_on": False,
        "last_updated": None
    },
    "music": {
        "playing": False,
        "current_track": "No track",
        "volume": 50,
        "track_position": 0,
        "playlist": ["track1.mp3", "track2.mp3", "track3.mp3", "track4.mp3"],
        "current_index": 0
    },
    "vehicle": {
        "doors_locked": False,
        "lights_on": False,
        "engine_running": True,
        "fuel_level": 75
    }
}

# Initialize pygame for music simulation
try:
    pygame.mixer.init()
    logger.info("🎵 Music system initialized")
except Exception as e:
    logger.warning(f"Music system initialization failed: {e}")

def get_complete_vehicle_state() -> Dict:
    """Get complete vehicle state formatted for frontend"""
    return {
        "climate": {
            "temperature": VEHICLE_STATE["climate"]["temperature"],
            "ac_on": VEHICLE_STATE["climate"]["ac_on"],
            "fan_speed": VEHICLE_STATE["climate"]["fan_speed"]
        },
        "music": {
            "playing": VEHICLE_STATE["music"]["playing"],
            "volume": VEHICLE_STATE["music"]["volume"],
            "current_track": VEHICLE_STATE["music"]["current_track"]
        },
        "vehicle": {
            "doors_locked": VEHICLE_STATE["vehicle"]["doors_locked"],
            "lights_on": VEHICLE_STATE["vehicle"]["lights_on"]
        }
    }

def update_vehicle_state(category: str, updates: Dict) -> Dict:
    """Update vehicle state and return formatted response for frontend"""
    VEHICLE_STATE[category].update(updates)
    VEHICLE_STATE[category]["last_updated"] = datetime.now().isoformat()
    
    logger.info(f"🚗 Vehicle state updated - {category}: {updates}")
    
    # Return complete state for frontend sync
    return get_complete_vehicle_state()

# ====================== CLIMATE CONTROL TOOLS ======================

class ClimateTools:
    """Climate control system tools"""
    
    @staticmethod
    async def set_temperature(temperature: int = 22) -> Dict:
        """Set cabin temperature"""
        try:
            # Validate temperature range
            temperature = max(16, min(30, temperature))
            
            updates = {
                "temperature": temperature,
                "ac_on": True if temperature < 25 else False
            }
            
            vehicle_state = update_vehicle_state("climate", updates)
            
            return {
                "success": True,
                "message": f"Temperature set to {temperature}°C",
                "vehicle_state": vehicle_state
            }
            
        except Exception as e:
            logger.error(f"Climate control error: {e}")
            return {"success": False, "message": f"Failed to set temperature: {e}"}
    
    @staticmethod
    async def set_fan_speed(speed: int = 2) -> Dict:
        """Set fan speed (1-5)"""
        try:
            speed = max(1, min(5, speed))
            vehicle_state = update_vehicle_state("climate", {"fan_speed": speed})
            
            return {
                "success": True,
                "message": f"Fan speed set to level {speed}",
                "vehicle_state": vehicle_state
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to set fan speed: {e}"}
    
    @staticmethod
    async def toggle_ac() -> Dict:
        """Toggle air conditioning on/off"""
        try:
            current_ac = VEHICLE_STATE["climate"]["ac_on"]
            new_ac_state = not current_ac
            
            vehicle_state = update_vehicle_state("climate", {"ac_on": new_ac_state})
            
            return {
                "success": True,
                "message": f"AC turned {'on' if new_ac_state else 'off'}",
                "vehicle_state": vehicle_state
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to toggle AC: {e}"}
    
    @staticmethod
    async def get_climate_status() -> Dict:
        """Get current climate status"""
        return {
            "success": True,
            "climate_state": VEHICLE_STATE["climate"],
            "vehicle_state": get_complete_vehicle_state()
        }

# ====================== MUSIC CONTROL TOOLS ======================

class MusicTools:
    """Music and entertainment system tools with FIXED pause/resume"""
    
    @staticmethod
    async def play_music(track_name: Optional[str] = None) -> Dict:
        """Play ACTUAL music from files"""
        try:
            music_dir = "data/music"
            playlist = VEHICLE_STATE["music"]["playlist"]
            current_index = VEHICLE_STATE["music"]["current_index"]
            
            # Handle case where no real files exist
            if not playlist or playlist[0] in ["No music files found", "Music system error"]:
                return {
                    "success": False,
                    "message": f"🎵 No music files found. Add MP3/WAV files to {os.path.abspath(music_dir)}/"
                }
            
            # If specific track requested, try to find it
            if track_name:
                for i, track in enumerate(playlist):
                    if track_name.lower() in track.lower():
                        current_index = i
                        break
            
            current_track = playlist[current_index] if playlist else "No track"
            track_path = os.path.join(music_dir, current_track)
            
            # Check if file actually exists
            if not os.path.exists(track_path):
                return {
                    "success": False,
                    "message": f"🎵 Music file not found: {current_track}"
                }
            
            # 🎵 ACTUALLY PLAY THE MUSIC!
            try:
                pygame.mixer.music.load(track_path)
                pygame.mixer.music.play()
                
                # 🔧 FIXED: Update pause state tracking
                MUSIC_PAUSED_STATE["is_paused"] = False
                MUSIC_PAUSED_STATE["current_file"] = track_path
                
                logger.info(f"🎵 ACTUALLY PLAYING: {current_track} from {track_path}")
                
                # Update state
                updates = {
                    "playing": True,
                    "current_track": current_track,
                    "current_index": current_index,
                    "track_position": 0
                }
                
                vehicle_state = update_vehicle_state("music", updates)
                
                return {
                    "success": True,
                    "message": f"🎵 Now playing: {current_track}",
                    "vehicle_state": vehicle_state
                }
                
            except pygame.error as e:
                logger.error(f"🎵 Pygame playback error: {e}")
                return {
                    "success": False,
                    "message": f"🎵 Cannot play {current_track}. Error: {str(e)}"
                }
            
        except Exception as e:
            logger.error(f"🎵 Music play error: {e}")
            return {"success": False, "message": f"Failed to play music: {e}"}
    
    @staticmethod
    async def pause_music() -> Dict:
        """🔧 FIXED: Pause/resume ACTUAL music playback with proper state tracking"""
        try:
            current_playing = VEHICLE_STATE["music"]["playing"]
            is_pygame_paused = MUSIC_PAUSED_STATE["is_paused"]
            
            logger.info(f"🎵 DEBUG: current_playing={current_playing}, is_pygame_paused={is_pygame_paused}")
            
            # Check if music is actually playing using pygame
            is_music_busy = pygame.mixer.music.get_busy()
            logger.info(f"🎵 DEBUG: pygame.mixer.music.get_busy()={is_music_busy}")
            
            if current_playing and not is_pygame_paused:
                # Currently playing - pause it
                pygame.mixer.music.pause()
                MUSIC_PAUSED_STATE["is_paused"] = True
                new_state = False  # UI shows paused
                message = "🎵 Music paused"
                logger.info("🎵 ACTUALLY PAUSED music")
                
            elif not current_playing and is_pygame_paused:
                # Currently paused - resume it
                pygame.mixer.music.unpause()
                MUSIC_PAUSED_STATE["is_paused"] = False
                new_state = True  # UI shows playing
                message = "🎵 Music resumed"
                logger.info("🎵 ACTUALLY RESUMED music")
                
            elif not current_playing and not is_pygame_paused:
                # Music was stopped or never started - restart the current track
                current_track = VEHICLE_STATE["music"]["current_track"]
                music_dir = "data/music"
                track_path = os.path.join(music_dir, current_track)
                
                if os.path.exists(track_path):
                    try:
                        pygame.mixer.music.load(track_path)
                        pygame.mixer.music.play()
                        MUSIC_PAUSED_STATE["is_paused"] = False
                        MUSIC_PAUSED_STATE["current_file"] = track_path
                        new_state = True
                        message = f"🎵 Restarted: {current_track}"
                        logger.info(f"🎵 RESTARTED music: {current_track}")
                    except pygame.error as e:
                        logger.error(f"🎵 Error restarting music: {e}")
                        return {"success": False, "message": f"Cannot restart music: {str(e)}"}
                else:
                    return {"success": False, "message": f"Music file not found: {current_track}"}
            else:
                # Edge case - force pause
                pygame.mixer.music.pause()
                MUSIC_PAUSED_STATE["is_paused"] = True
                new_state = False
                message = "🎵 Music paused (forced)"
                logger.info("🎵 FORCED PAUSE")
            
            vehicle_state = update_vehicle_state("music", {"playing": new_state})
            
            return {
                "success": True,
                "message": message,
                "vehicle_state": vehicle_state
            }
            
        except Exception as e:
            logger.error(f"🎵 Pause/resume error: {e}")
            return {"success": False, "message": f"Failed to pause/resume music: {e}"}
    
    @staticmethod
    async def next_track() -> Dict:
        """Switch to next track and ACTUALLY play it"""
        try:
            playlist = VEHICLE_STATE["music"]["playlist"]
            current_index = VEHICLE_STATE["music"]["current_index"]
            
            if not playlist or playlist[0] in ["No music files found", "Music system error"]:
                return {"success": False, "message": "No music files available"}
            
            # Move to next track (loop back to start if at end)
            next_index = (current_index + 1) % len(playlist)
            next_track = playlist[next_index]
            
            # Stop current music
            pygame.mixer.music.stop()
            
            # Load and play next track
            music_dir = "data/music"
            track_path = os.path.join(music_dir, next_track)
            
            if os.path.exists(track_path):
                try:
                    pygame.mixer.music.load(track_path)
                    pygame.mixer.music.play()
                    
                    # 🔧 FIXED: Update pause state
                    MUSIC_PAUSED_STATE["is_paused"] = False
                    MUSIC_PAUSED_STATE["current_file"] = track_path
                    
                    logger.info(f"🎵 ACTUALLY PLAYING NEXT: {next_track}")
                    
                    updates = {
                        "current_index": next_index,
                        "current_track": next_track,
                        "track_position": 0,
                        "playing": True
                    }
                    
                    vehicle_state = update_vehicle_state("music", updates)
                    
                    return {
                        "success": True,
                        "message": f"🎵 Next track: {next_track}",
                        "vehicle_state": vehicle_state
                    }
                    
                except pygame.error as e:
                    logger.error(f"🎵 Error playing next track: {e}")
                    return {"success": False, "message": f"Cannot play {next_track}: {str(e)}"}
            else:
                return {"success": False, "message": f"Next track file not found: {next_track}"}
                
        except Exception as e:
            return {"success": False, "message": f"Failed to switch track: {e}"}
    
    @staticmethod
    async def previous_track() -> Dict:
        """Switch to previous track and ACTUALLY play it"""
        try:
            playlist = VEHICLE_STATE["music"]["playlist"]
            current_index = VEHICLE_STATE["music"]["current_index"]
            
            if not playlist or playlist[0] in ["No music files found", "Music system error"]:
                return {"success": False, "message": "No music files available"}
            
            # Move to previous track (loop to end if at start)
            prev_index = (current_index - 1) % len(playlist)
            prev_track = playlist[prev_index]
            
            # Stop current music
            pygame.mixer.music.stop()
            
            # Load and play previous track
            music_dir = "data/music"
            track_path = os.path.join(music_dir, prev_track)
            
            if os.path.exists(track_path):
                try:
                    pygame.mixer.music.load(track_path)
                    pygame.mixer.music.play()
                    
                    # 🔧 FIXED: Update pause state
                    MUSIC_PAUSED_STATE["is_paused"] = False
                    MUSIC_PAUSED_STATE["current_file"] = track_path
                    
                    logger.info(f"🎵 ACTUALLY PLAYING PREVIOUS: {prev_track}")
                    
                    updates = {
                        "current_index": prev_index,
                        "current_track": prev_track,
                        "track_position": 0,
                        "playing": True
                    }
                    
                    vehicle_state = update_vehicle_state("music", updates)
                    
                    return {
                        "success": True,
                        "message": f"🎵 Previous track: {prev_track}",
                        "vehicle_state": vehicle_state
                    }
                    
                except pygame.error as e:
                    logger.error(f"🎵 Error playing previous track: {e}")
                    return {"success": False, "message": f"Cannot play {prev_track}: {str(e)}"}
            else:
                return {"success": False, "message": f"Previous track file not found: {prev_track}"}
                
        except Exception as e:
            return {"success": False, "message": f"Failed to switch track: {e}"}
    
    @staticmethod
    async def set_volume(volume: int = 50) -> Dict:
        """Set ACTUAL music volume"""
        try:
            volume = max(0, min(100, volume))
            
            # Set pygame mixer volume (0.0 to 1.0)
            pygame_volume = volume / 100.0
            pygame.mixer.music.set_volume(pygame_volume)
            
            logger.info(f"🎵 ACTUALLY SET VOLUME to {volume}% (pygame: {pygame_volume})")
            
            vehicle_state = update_vehicle_state("music", {"volume": volume})
            
            return {
                "success": True,
                "message": f"🎵 Volume set to {volume}%",
                "vehicle_state": vehicle_state
            }
            
        except Exception as e:
            return {"success": False, "message": f"Failed to set volume: {e}"}
    
    @staticmethod
    async def get_music_status() -> Dict:
        """Get current music system status with pause state"""
        return {
            "success": True,
            "music_state": VEHICLE_STATE["music"],
            "pause_state": MUSIC_PAUSED_STATE,
            "pygame_busy": pygame.mixer.music.get_busy(),
            "vehicle_state": get_complete_vehicle_state()
        }

# ====================== VEHICLE CONTROL TOOLS ======================

class VehicleTools:
    """Vehicle system control tools"""
    
    @staticmethod
    async def lock_doors() -> Dict:
        """Lock all vehicle doors"""
        try:
            vehicle_state = update_vehicle_state("vehicle", {"doors_locked": True})
            
            return {
                "success": True,
                "message": "All doors locked",
                "vehicle_state": vehicle_state
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to lock doors: {e}"}
    
    @staticmethod
    async def unlock_doors() -> Dict:
        """Unlock vehicle doors"""
        try:
            vehicle_state = update_vehicle_state("vehicle", {"doors_locked": False})
            
            return {
                "success": True,
                "message": "Doors unlocked",
                "vehicle_state": vehicle_state
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to unlock doors: {e}"}
    
    @staticmethod
    async def toggle_lights() -> Dict:
        """Toggle vehicle lights"""
        try:
            current_lights = VEHICLE_STATE["vehicle"]["lights_on"]
            new_lights_state = not current_lights
            
            vehicle_state = update_vehicle_state("vehicle", {"lights_on": new_lights_state})
            
            return {
                "success": True,
                "message": f"Lights turned {'on' if new_lights_state else 'off'}",
                "vehicle_state": vehicle_state
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to toggle lights: {e}"}
    
    @staticmethod
    async def get_vehicle_status() -> Dict:
        """Get comprehensive vehicle status"""
        return {
            "success": True,
            "vehicle_state": VEHICLE_STATE["vehicle"],
            "complete_state": get_complete_vehicle_state()
        }

# ====================== NAVIGATION TOOLS ======================

class NavigationTools:
    """Enhanced navigation with comprehensive place search and tourist attractions"""
    
    # 🔧 ENHANCED: Comprehensive mock data for different place types in Eluru
    MOCK_PLACES_DATA = {
        "tourist_attraction": [
            {"name": "Eluru Ashram", "distance": 2.1, "rating": 4.3, "category": "Spiritual Site"},
            {"name": "Kolleru Lake Bird Sanctuary", "distance": 15.2, "rating": 4.5, "category": "Nature Reserve"},
            {"name": "Dwaraka Tirumala Temple", "distance": 18.7, "rating": 4.6, "category": "Religious Site"},
            {"name": "Buddha Park Eluru", "distance": 3.2, "rating": 4.1, "category": "Park"},
            {"name": "Eluru Municipal Park", "distance": 1.8, "rating": 3.9, "category": "Recreation"},
            {"name": "Sri Venkateswara Temple", "distance": 2.5, "rating": 4.4, "category": "Temple"},
            {"name": "Tanuku Beach", "distance": 25.3, "rating": 4.2, "category": "Beach"},
            {"name": "Jangareddygudem", "distance": 35.6, "rating": 4.0, "category": "Hill Station"},
            {"name": "Eluru Fort Ruins", "distance": 4.1, "rating": 3.8, "category": "Historical Site"},
            {"name": "Krishna River Ghats", "distance": 5.2, "rating": 4.2, "category": "Scenic Spot"}
        ],
        "restaurant": [
            {"name": "Udupi Sri Krishna Bhavan", "distance": 1.2, "rating": 4.3, "category": "South Indian"},
            {"name": "Hotel Swagruha", "distance": 0.9, "rating": 4.1, "category": "Multi-cuisine"},
            {"name": "Kakatiya Deluxe", "distance": 1.5, "rating": 4.0, "category": "Vegetarian"},
            {"name": "Minerva Coffee Shop", "distance": 1.1, "rating": 4.2, "category": "Coffee & Snacks"},
            {"name": "Paradise Restaurant", "distance": 2.1, "rating": 4.4, "category": "Biryani"},
            {"name": "Hotel Sitara", "distance": 1.8, "rating": 3.9, "category": "Family Restaurant"},
            {"name": "Bawarchi Restaurant", "distance": 1.7, "rating": 4.1, "category": "North Indian"},
            {"name": "Sandhya Tiffin Center", "distance": 0.8, "rating": 4.0, "category": "Breakfast"}
        ],
        "lodging": [
            # 🔧 UPDATED: Better hotel data for Eluru
            {"name": "Hotel Vinayaka", "distance": 1.2, "rating": 4.3, "category": "3-Star Hotel"},
            {"name": "Hotel Sri Sai International", "distance": 1.5, "rating": 4.1, "category": "4-Star Hotel"},
            {"name": "Hotel Dwaraka", "distance": 0.8, "rating": 3.9, "category": "Budget Hotel"},
            {"name": "Hotel Sree Kanya", "distance": 1.1, "rating": 4.0, "category": "3-Star Hotel"},
            {"name": "Manya Guestline", "distance": 1.0, "rating": 3.2, "category": "Budget Hotel"},
            {"name": "Hotel Surya Residency", "distance": 1.1, "rating": 3.4, "category": "Business Hotel"},
            {"name": "Hotel Raj Palace", "distance": 1.3, "rating": 3.8, "category": "Comfort Hotel"},
            {"name": "Haritha Hotel", "distance": 2.1, "rating": 4.0, "category": "Government Hotel"}
        ],
        "place_of_worship": [
            {"name": "Sri Venkateswara Swamy Temple", "distance": 2.5, "rating": 4.6, "category": "Hindu Temple"},
            {"name": "Eluru Jama Masjid", "distance": 1.8, "rating": 4.2, "category": "Mosque"},
            {"name": "St. Anthony's Church", "distance": 2.1, "rating": 4.3, "category": "Christian Church"},
            {"name": "Ganesha Temple", "distance": 1.5, "rating": 4.4, "category": "Hindu Temple"},
            {"name": "Hanuman Temple", "distance": 1.2, "rating": 4.1, "category": "Hindu Temple"},
            {"name": "Shirdi Sai Baba Temple", "distance": 3.2, "rating": 4.5, "category": "Spiritual Center"},
            {"name": "Rama Temple", "distance": 2.8, "rating": 4.0, "category": "Hindu Temple"},
            {"name": "Anjaneya Temple", "distance": 1.9, "rating": 4.2, "category": "Hindu Temple"}
        ],
        "shopping_mall": [
            {"name": "Adithya Central", "distance": 1.5, "rating": 4.1, "category": "Shopping Mall"},
            {"name": "Eluru Shopping Complex", "distance": 1.2, "rating": 3.8, "category": "Shopping Center"},
            {"name": "City Mall Eluru", "distance": 1.8, "rating": 3.9, "category": "Shopping Mall"},
            {"name": "Textile Market", "distance": 1.0, "rating": 3.7, "category": "Traditional Market"},
            {"name": "Gandhi Bazar", "distance": 0.8, "rating": 4.0, "category": "Local Market"},
            {"name": "Main Road Shopping", "distance": 1.1, "rating": 3.6, "category": "Street Shopping"},
            {"name": "Cloth Merchants Street", "distance": 1.3, "rating": 3.8, "category": "Textile Market"},
            {"name": "Electronics Market", "distance": 1.4, "rating": 3.5, "category": "Electronics"}
        ],
        "hospital": [
            {"name": "Government General Hospital", "distance": 1.8, "rating": 3.9, "category": "Government Hospital"},
            {"name": "Eluru Multi-Specialty Hospital", "distance": 2.1, "rating": 4.2, "category": "Private Hospital"},
            {"name": "Apollo Clinic", "distance": 1.5, "rating": 4.0, "category": "Clinic"},
            {"name": "Dr. Reddy's Hospital", "distance": 1.7, "rating": 3.8, "category": "Private Hospital"},
            {"name": "City Hospital", "distance": 1.3, "rating": 3.7, "category": "Multi-specialty"},
            {"name": "Nursing Home", "distance": 1.0, "rating": 3.6, "category": "Nursing Home"},
            {"name": "Eye Care Center", "distance": 1.4, "rating": 4.1, "category": "Specialty Clinic"},
            {"name": "Dental Clinic", "distance": 1.2, "rating": 3.9, "category": "Dental Care"}
        ],
        "gas_station": [
            {"name": "Indian Oil Petrol Pump", "distance": 1.1, "rating": 3.8, "category": "Fuel Station"},
            {"name": "HP Gas Station", "distance": 1.3, "rating": 3.9, "category": "Fuel Station"},
            {"name": "Bharat Petroleum", "distance": 0.9, "rating": 3.7, "category": "Fuel Station"},
            {"name": "Reliance Petrol Pump", "distance": 1.5, "rating": 4.0, "category": "Fuel Station"},
            {"name": "Shell Petrol Station", "distance": 1.8, "rating": 3.8, "category": "Fuel Station"},
            {"name": "Essar Petrol Pump", "distance": 2.1, "rating": 3.6, "category": "Fuel Station"}
        ],
        "cafe": [
            {"name": "Coffee Day", "distance": 1.2, "rating": 4.0, "category": "Coffee Chain"},
            {"name": "Barista Cafe", "distance": 1.4, "rating": 4.1, "category": "Coffee Shop"},
            {"name": "Local Coffee House", "distance": 0.8, "rating": 3.9, "category": "Traditional Cafe"},
            {"name": "Tea Point", "distance": 1.0, "rating": 3.8, "category": "Tea Shop"},
            {"name": "Juice Corner", "distance": 1.1, "rating": 4.0, "category": "Juice Bar"},
            {"name": "Snack Cafe", "distance": 1.3, "rating": 3.7, "category": "Snack Bar"}
        ],
        "bank": [
            {"name": "State Bank of India", "distance": 1.0, "rating": 3.8, "category": "Public Bank"},
            {"name": "HDFC Bank", "distance": 1.2, "rating": 4.0, "category": "Private Bank"},
            {"name": "ICICI Bank", "distance": 1.1, "rating": 3.9, "category": "Private Bank"},
            {"name": "Andhra Bank", "distance": 0.9, "rating": 3.7, "category": "Regional Bank"},
            {"name": "Axis Bank", "distance": 1.3, "rating": 3.8, "category": "Private Bank"},
            {"name": "Bank of Baroda", "distance": 1.4, "rating": 3.6, "category": "Public Bank"}
        ]
    }
    
    @staticmethod
    async def get_current_location(latitude: Optional[float] = None, longitude: Optional[float] = None) -> Dict:
        """Get current GPS location with reverse geocoding"""
        try:
            # Use real coordinates if provided, otherwise fallback
            if latitude is not None and longitude is not None:
                logger.info(f"🌍 Using real browser location: {latitude}, {longitude}")
                
                # Try Google Maps reverse geocoding
                address = await NavigationTools._get_address_from_coords(latitude, longitude)
                if not address:
                    address = f"Location: {latitude:.4f}°N, {longitude:.4f}°E"
                
                # Format response prioritizing city name
                if "," in address:
                    address_parts = [part.strip() for part in address.split(',')]
                    # Use the most specific location parts
                    if len(address_parts) >= 3:
                        location_message = f"📍 You are in {address_parts[0]}, {address_parts[1]}, {address_parts[2]}"
                    elif len(address_parts) >= 2:
                        location_message = f"📍 You are in {address_parts[0]}, {address_parts[1]}"
                    else:
                        location_message = f"📍 Your current location: {address}"
                else:
                    location_message = f"📍 Your current location: {address}"
                
                return {
                    "success": True,
                    "message": location_message,
                    "full_address": address,
                    "latitude": latitude,
                    "longitude": longitude,
                    "address": address
                }
            else:
                # Fallback location
                return {
                    "success": True,
                    "message": "📍 Your current location: Eluru, Andhra Pradesh, India",
                    "full_address": "Eluru, Andhra Pradesh, India",
                    "latitude": 16.7206,
                    "longitude": 81.1071,
                    "address": "Eluru, Andhra Pradesh, India"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Unable to get current location: {e}"
            }
    
    @staticmethod
    async def get_directions(destination: str, latitude: Optional[float] = None, longitude: Optional[float] = None) -> Dict:
        """Get directions to destination"""
        try:
            # Use provided coordinates or fallback
            start_lat = latitude if latitude is not None else 16.7206
            start_lon = longitude if longitude is not None else 81.1071
            
            logger.info(f"🗺️ Getting directions to '{destination}' from {start_lat}, {start_lon}")
            
            # Try Google Directions API
            google_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
            if google_api_key:
                directions = await NavigationTools._get_google_directions(start_lat, start_lon, destination, google_api_key)
                if directions:
                    return {
                        "success": True,
                        "message": directions['summary'],
                        "directions": directions
                    }
            
            # Fallback response
            maps_url = f"https://www.google.com/maps/dir/{start_lat},{start_lon}/{destination.replace(' ', '+')}"
            
            response = f"🧭 Navigation to {destination}\n"
            response += f"📍 Destination: {destination}\n"
            response += f"📏 Distance: Calculating...\n"
            response += f"⏱️ Duration: Calculating...\n"
            response += f"\n🌐 Open in Google Maps: {maps_url}"
            
            return {
                "success": True,
                "message": response,
                "maps_url": maps_url
            }
            
        except Exception as e:
            logger.error(f"Directions error: {e}")
            return {
                "success": False,
                "message": f"Unable to get directions to {destination}: {e}"
            }
    
    @staticmethod
    async def search_nearby_places(place_type: str, latitude: Optional[float] = None, longitude: Optional[float] = None, radius_km: int = 5) -> Dict:
        """🔧 ENHANCED: Search for nearby places with comprehensive tourist attractions"""
        try:
            # Use provided coordinates or fallback
            search_lat = latitude if latitude is not None else 16.7206
            search_lon = longitude if longitude is not None else 81.1071
            
            logger.info(f"🔍 Enhanced search for {place_type} near {search_lat}, {search_lon}")
            
            # Try Google Places API first
            google_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
            if google_api_key:
                places = await NavigationTools._search_google_places(search_lat, search_lon, place_type, radius_km, google_api_key)
                if places and len(places) >= 3:  # Only use Google if we get good results
                    return NavigationTools._format_places_response(places, place_type)
            
            # Enhanced fallback with comprehensive mock data
            mock_places = NavigationTools._get_enhanced_mock_places(place_type)
            return NavigationTools._format_places_response(mock_places, place_type)
            
        except Exception as e:
            logger.error(f"Place search error: {e}")
            # Emergency fallback
            emergency_places = [
                {"name": f"Local {place_type.title()} 1", "distance": 1.2, "rating": 4.0, "category": "Local"},
                {"name": f"Local {place_type.title()} 2", "distance": 1.8, "rating": 3.8, "category": "Local"},
                {"name": f"Local {place_type.title()} 3", "distance": 2.1, "rating": 4.1, "category": "Local"}
            ]
            return NavigationTools._format_places_response(emergency_places, place_type)
    
    @staticmethod
    def _get_enhanced_mock_places(place_type: str) -> List[Dict]:
        """🔧 ENHANCED: Get comprehensive mock places for different types"""
        # Get base places for the type
        base_places = NavigationTools.MOCK_PLACES_DATA.get(place_type, [])
        
        if base_places:
            # Add some random variation to distances and ratings
            enhanced_places = []
            for place in base_places:
                enhanced_place = place.copy()
                # Add slight random variation to make it more realistic
                enhanced_place["distance"] += random.uniform(-0.2, 0.3)
                enhanced_place["distance"] = max(0.1, enhanced_place["distance"])  # Ensure positive
                enhanced_place["rating"] += random.uniform(-0.1, 0.2)
                enhanced_place["rating"] = min(5.0, max(3.0, enhanced_place["rating"]))  # Keep in range
                enhanced_places.append(enhanced_place)
            
            # Sort by distance and return up to 8 places
            enhanced_places.sort(key=lambda x: x['distance'])
            return enhanced_places[:8]
        
        # Generic fallback for unknown types
        return [
            {"name": f"Popular {place_type.title().replace('_', ' ')} Spot", "distance": 1.5, "rating": 4.2, "category": "Popular"},
            {"name": f"Recommended {place_type.title().replace('_', ' ')}", "distance": 2.1, "rating": 4.0, "category": "Recommended"},
            {"name": f"Local {place_type.title().replace('_', ' ')} Choice", "distance": 1.8, "rating": 3.9, "category": "Local Favorite"},
            {"name": f"Top-rated {place_type.title().replace('_', ' ')}", "distance": 2.5, "rating": 4.3, "category": "Highly Rated"}
        ]
    
    @staticmethod
    def _extract_place_type(message: str) -> str:
        """🔧 ENHANCED: Extract place type with comprehensive tourist attraction support"""
        message_lower = message.lower()
        
        # 🔧 ENHANCED: Tourist attractions and sightseeing
        if any(word in message_lower for word in [
            'visit', 'tourist', 'attraction', 'sightseeing', 'landmark', 'monument', 
            'places to visit', 'tourist attractions', 'sightseeing spots', 'points of interest',
            'tourist places', 'visiting spots', 'places to see', 'must visit', 'tourist spots',
            'scenic places', 'beautiful places', 'famous places', 'popular places'
        ]):
            logger.info("🔧 Detected tourist attraction request")
            return 'tourist_attraction'
        
        # 🔧 ENHANCED: Hotels/lodging detection
        elif any(word in message_lower for word in ['hotel', 'hotels', 'lodging', 'accommodation', 'stay', 'guest house', 'resort']):
            logger.info("🔧 Detected hotel/lodging request")
            return 'lodging'
        
        # 🔧 ENHANCED: Restaurants and dining
        elif any(word in message_lower for word in ['restaurant', 'restaurants', 'food', 'eat', 'dine', 'dining', 'meal', 'lunch', 'dinner', 'breakfast']):
            logger.info("🔧 Detected restaurant request")
            return 'restaurant'
        
        # 🔧 ENHANCED: Places of worship
        elif any(word in message_lower for word in ['temple', 'temples', 'church', 'churches', 'mosque', 'mosques', 'worship', 'religious', 'pray', 'prayer', 'shrine']):
            logger.info("🔧 Detected worship place request")
            return 'place_of_worship'
        
        # 🔧 ENHANCED: Shopping
        elif any(word in message_lower for word in ['mall', 'shopping', 'store', 'shop', 'shops', 'market', 'shopping center', 'bazaar', 'retail']):
            logger.info("🔧 Detected shopping request")
            return 'shopping_mall'
        
        # Medical facilities
        elif any(word in message_lower for word in ['hospital', 'hospitals', 'medical', 'clinic', 'doctor', 'health', 'pharmacy', 'medical center']):
            logger.info("🔧 Detected hospital request")
            return 'hospital'
        
        # Coffee shops and cafes
        elif any(word in message_lower for word in ['coffee', 'cafe', 'cafes', 'coffee shop', 'tea', 'beverages']):
            logger.info("🔧 Detected cafe request")
            return 'cafe'
        
        # Gas stations
        elif any(word in message_lower for word in ['gas', 'fuel', 'petrol', 'station', 'gas station', 'fuel station']):
            logger.info("🔧 Detected gas station request")
            return 'gas_station'
        
        # Banks and ATMs
        elif any(word in message_lower for word in ['bank', 'banks', 'atm', 'banking', 'financial']):
            logger.info("🔧 Detected bank request")
            return 'bank'
        
        # Default to tourist attractions for general "places" queries
        elif any(word in message_lower for word in ['places', 'spots', 'locations', 'areas']):
            logger.info("🔧 Detected general places request - defaulting to tourist attractions")
            return 'tourist_attraction'
        
        # Generic establishment fallback
        else:
            logger.info("🔧 Using default establishment type")
            return 'establishment'
    
    @staticmethod
    async def get_weather(location: Optional[str] = None, latitude: Optional[float] = None, longitude: Optional[float] = None) -> Dict:
        """Get weather information"""
        try:
            api_key = os.getenv("OPENWEATHER_API_KEY")
            
            if not api_key:
                logger.warning("OpenWeather API key not found, using mock data")
                return await NavigationTools._get_mock_weather(location, latitude, longitude)
            
            # Determine API endpoint
            if location:
                # City-based weather
                clean_location = location.strip().title()
                if not any(country in clean_location.lower() for country in [',in', ',india']):
                    # Add India for better accuracy
                    indian_cities = ['chennai', 'mumbai', 'delhi', 'bangalore', 'hyderabad', 'pune', 'kolkata']
                    if clean_location.lower() in indian_cities:
                        clean_location += ',IN'
                
                url = f"https://api.openweathermap.org/data/2.5/weather?q={clean_location}&appid={api_key}&units=metric"
                
            elif latitude is not None and longitude is not None:
                # Coordinate-based weather
                url = f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={api_key}&units=metric"
                
            else:
                # Fallback coordinates
                url = f"https://api.openweathermap.org/data/2.5/weather?lat=16.7206&lon=81.1071&appid={api_key}&units=metric"
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return NavigationTools._format_weather_response(data)
                    elif response.status == 404:
                        if location:
                            return {
                                "success": False,
                                "message": f"❌ Sorry, I couldn't find weather information for '{location}'. Please check the city name and try again."
                            }
                        else:
                            return await NavigationTools._get_mock_weather(location, latitude, longitude)
                    else:
                        logger.warning(f"OpenWeather API error: {response.status}")
                        return await NavigationTools._get_mock_weather(location, latitude, longitude)
            
        except Exception as e:
            logger.error(f"Weather API request failed: {e}")
            return await NavigationTools._get_mock_weather(location, latitude, longitude)
    
    @staticmethod
    async def get_traffic_info(route: Optional[str] = None) -> Dict:
        """Get traffic information"""
        return {
            "success": True,
            "message": f"🚦 Traffic status: {random.choice(['light', 'moderate', 'heavy'])}, {random.randint(0, 30)} minutes delay"
        }
    
    # Helper methods
    @staticmethod
    def _format_places_response(places: List[Dict], place_type: str) -> Dict:
        """🔧 ENHANCED: Format places response with better descriptions"""
        if not places:
            suggestions = {
                'tourist_attraction': "Try searching for 'temples', 'parks', or 'landmarks'",
                'restaurant': "Try searching for 'food', 'dining', or specific cuisines",
                'lodging': "Try searching for 'hotels' or 'accommodation'",
                'shopping_mall': "Try searching for 'markets' or 'shopping centers'"
            }
            
            return {
                "success": True,
                "message": f"No {place_type.replace('_', ' ')} found nearby. {suggestions.get(place_type, 'Try a different search term.')}",
                "places": [],
                "suggestion": suggestions.get(place_type, "Try a different search term")
            }
        
        # Create enhanced user-readable message
        place_type_display = place_type.replace('_', ' ').title()
        if place_type == 'tourist_attraction':
            place_type_display = "places to visit"
        elif place_type == 'place_of_worship':
            place_type_display = "religious places"
        elif place_type == 'lodging':
            place_type_display = "hotels"
        
        message = f"🔍 Found {len(places)} {place_type_display} near you:\n\n"
        
        for i, place in enumerate(places[:8]):  # Show up to 8 places
            name = place['name']
            distance = place['distance']
            category = place.get('category', 'Local Business')
            
            place_info = f"📍 {name}"
            
            # Add category info
            if category and category != 'Local Business':
                place_info += f" ({category})"
            
            # Add distance
            if distance < 1:
                place_info += f" - {int(distance * 1000)}m away"
            else:
                place_info += f" - {distance:.1f}km away"
            
            # Add rating if available
            if place.get('rating'):
                place_info += f" ⭐ {place['rating']}/5"
            
            message += f"{i+1}. {place_info}\n"
        
        # Enhanced suggestions based on place type
        suggestion_text = "💡 Say 'navigate to [place name]' for directions"
        if place_type == 'tourist_attraction':
            suggestion_text += " or ask about 'restaurants near [place name]'"
        elif place_type == 'restaurant':
            suggestion_text += " or ask about 'hotels near [restaurant name]'"
        
        message += f"\n{suggestion_text}"
        
        return {
            "success": True,
            "message": message,
            "places": places,
            "place_type": place_type,
            "count": len(places),
            "suggestion": suggestion_text
        }
    
    @staticmethod
    async def _get_google_directions(start_lat: float, start_lon: float, destination: str, api_key: str) -> Optional[Dict]:
        """Get directions using Google Directions API"""
        try:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": f"{start_lat},{start_lon}",
                "destination": destination,
                "key": api_key,
                "units": "metric"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == "OK" and data.get("routes"):
                            route = data["routes"][0]
                            leg = route["legs"][0]
                            
                            distance = leg["distance"]["text"]
                            duration = leg["duration"]["text"]
                            end_address = leg["end_address"]
                            
                            # Extract turn-by-turn instructions
                            instructions = []
                            for step in leg["steps"]:
                                instruction = step["html_instructions"]
                                # Clean HTML tags
                                instruction = re.sub('<.*?>', '', instruction)
                                step_distance = step["distance"]["text"]
                                instructions.append(f"{instruction} ({step_distance})")
                            
                            # Create Google Maps URL
                            maps_url = f"https://www.google.com/maps/dir/{start_lat},{start_lon}/{destination.replace(' ', '+')}"
                            
                            # Format response
                            response = f"🧭 Navigation Route\n"
                            response += f"📍 Destination: {end_address}\n"
                            response += f"📏 Distance: {distance}\n"
                            response += f"⏱️ Duration: {duration}\n"
                            
                            if len(instructions) > 0:
                                response += f"\n🗺️ Turn-by-Turn Directions:\n"
                                for i, instruction in enumerate(instructions[:6], 1):  # Show first 6 steps
                                    response += f"{i}. {instruction}\n"
                                
                                if len(instructions) > 6:
                                    response += f"... and {len(instructions) - 6} more steps\n"
                            
                            response += f"\n🌐 Open in Google Maps: {maps_url}"
                            
                            return {
                                "summary": response,
                                "distance": distance,
                                "duration": duration,
                                "instructions": instructions,
                                "end_address": end_address,
                                "maps_url": maps_url
                            }
                            
        except Exception as e:
            logger.warning(f"Google Directions API failed: {e}")
        
        return None
    
    @staticmethod
    async def _search_google_places(latitude: float, longitude: float, place_type: str, radius_km: int, api_key: str) -> List[Dict]:
        """🔧 ENHANCED: Search using Google Places API with comprehensive type mapping"""
        try:
            radius_m = min(radius_km * 1000, 50000)
            
            # 🔧 ENHANCED: Comprehensive Google Places type mapping
            google_types = {
                "tourist_attraction": "tourist_attraction",
                "point_of_interest": "point_of_interest", 
                "restaurant": "restaurant",
                "gas_station": "gas_station",
                "cafe": "cafe", 
                "hospital": "hospital",
                "shopping_mall": "shopping_mall",
                "place_of_worship": "place_of_worship",
                "lodging": "lodging",
                "hotel": "lodging",
                "hotels": "lodging",
                "temple": "place_of_worship",
                "temples": "place_of_worship",
                "bank": "bank",
                "pharmacy": "pharmacy",
                "school": "school", 
                "police": "police",
                "establishment": "establishment"
            }
            
            google_type = google_types.get(place_type, "establishment")
            logger.info(f"🔧 Mapping place_type '{place_type}' to Google type '{google_type}'")
            
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{latitude},{longitude}",
                "radius": radius_m,
                "type": google_type,
                "key": api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == "OK":
                            places = []
                            for result in data.get("results", [])[:10]:  # Get up to 10 results
                                place_location = result.get("geometry", {}).get("location", {})
                                place_lat = place_location.get("lat")
                                place_lng = place_location.get("lng")
                                
                                if place_lat and place_lng:
                                    distance = NavigationTools._calculate_distance(latitude, longitude, place_lat, place_lng)
                                    
                                    # Determine category from place types
                                    place_types = result.get("types", [])
                                    category = NavigationTools._determine_category(place_types)
                                    
                                    places.append({
                                        'name': result.get("name", "Unknown Place"),
                                        'distance': distance,
                                        'rating': result.get("rating"),
                                        'address': result.get("vicinity", ""),
                                        'place_id': result.get("place_id"),
                                        'types': place_types,
                                        'category': category
                                    })
                            
                            # Sort by distance
                            places.sort(key=lambda x: x['distance'])
                            logger.info(f"🔧 Found {len(places)} places of type '{google_type}'")
                            return places
                            
        except Exception as e:
            logger.warning(f"Google Places API search failed: {e}")
        
        return []
    
    @staticmethod
    def _determine_category(place_types: List[str]) -> str:
        """🔧 ENHANCED: Determine category from Google Places types"""
        type_categories = {
            "tourist_attraction": "Tourist Attraction",
            "place_of_worship": "Religious Site",
            "restaurant": "Restaurant",
            "lodging": "Hotel",
            "hospital": "Medical",
            "shopping_mall": "Shopping",
            "bank": "Financial",
            "gas_station": "Fuel Station",
            "cafe": "Cafe",
            "park": "Recreation",
            "museum": "Cultural Site",
            "amusement_park": "Entertainment",
            "zoo": "Wildlife",
            "church": "Religious Site",
            "hindu_temple": "Temple",
            "mosque": "Religious Site"
        }
        
        for place_type in place_types:
            if place_type in type_categories:
                return type_categories[place_type]
        
        return "Local Business"
    
    @staticmethod
    def _format_weather_response(api_data: Dict) -> Dict:
        """Format weather response"""
        try:
            location_name = api_data.get("name", "Unknown")
            country = api_data.get("sys", {}).get("country", "")
            
            location_display = f"{location_name}, {country}" if country else location_name
            
            main = api_data.get("main", {})
            weather = api_data.get("weather", [{}])[0]
            wind = api_data.get("wind", {})
            
            temperature = round(main.get("temp", 0))
            feels_like = round(main.get("feels_like", 0))
            description = weather.get("description", "").title()
            humidity = main.get("humidity", 0)
            wind_speed = round(wind.get("speed", 0) * 3.6, 1)  # Convert m/s to km/h
            
            message = f"🌤️ Weather in {location_display}: {temperature}°C, {description}"
            if feels_like != temperature:
                message += f" (feels like {feels_like}°C)"
            message += f"\n💧 Humidity: {humidity}%"
            message += f"\n💨 Wind: {wind_speed} km/h"
            
            return {
                "success": True,
                "message": message,
                "weather": {
                    "location": location_display,
                    "temperature": temperature,
                    "description": description,
                    "humidity": humidity,
                    "wind_speed": wind_speed
                }
            }
            
        except Exception as e:
            logger.error(f"Error formatting weather response: {e}")
            return NavigationTools._get_mock_weather("Unknown Location")
    
    @staticmethod
    async def _get_mock_weather(location: Optional[str] = None, latitude: Optional[float] = None, longitude: Optional[float] = None) -> Dict:
        """Mock weather data fallback"""
        if location:
            location_display = location
        elif latitude is not None and longitude is not None:
            location_display = f"Your Location ({latitude:.2f}, {longitude:.2f})"
        else:
            location_display = "Eluru, Andhra Pradesh, India"
        
        temp = random.randint(22, 35)
        conditions = random.choice(["partly cloudy", "sunny", "light rain", "overcast"])
        humidity = random.randint(60, 90)
        wind = random.randint(5, 20)
        
        return {
            "success": True,
            "message": f"🌤️ Weather in {location_display}: {temp}°C, {conditions} (mock data)\n💧 Humidity: {humidity}%\n💨 Wind: {wind} km/h"
        }
    
    @staticmethod
    async def _get_address_from_coords(latitude: float, longitude: float) -> Optional[str]:
        """Get address using Google Geocoding API"""
        try:
            google_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
            if not google_api_key:
                return None
            
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "latlng": f"{latitude},{longitude}",
                "key": google_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == "OK" and data.get("results"):
                            result = data["results"][0]
                            
                            # Extract city, state, country
                            address_components = result.get("address_components", [])
                            city = ""
                            state = ""
                            country = ""
                            
                            for component in address_components:
                                types = component.get("types", [])
                                if "locality" in types:
                                    city = component.get("long_name", "")
                                elif "administrative_area_level_1" in types:
                                    state = component.get("short_name", "")
                                elif "country" in types:
                                    country = component.get("short_name", "")
                            
                            # Format nicely
                            if city and state and country:
                                return f"{city}, {state}, {country}"
                            elif city and country:
                                return f"{city}, {country}"
                            else:
                                formatted_address = result.get("formatted_address", "")
                                if formatted_address:
                                    parts = formatted_address.split(',')
                                    if len(parts) >= 2:
                                        return f"{parts[0].strip()}, {parts[-1].strip()}"
                                    return parts[0].strip()
                                    
        except Exception as e:
            logger.warning(f"Google Geocoding failed: {e}")
        
        return None
    
    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        import math
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return c * 6371  # Earth's radius in km

# ====================== VEHICLE INFORMATION TOOLS ======================

class VehicleInfoTools:
    """Vehicle information database tools"""
    
    # Vehicle database
    VEHICLE_DB = {
        "tesla_model_3": {
            "name": "Tesla Model 3",
            "type": "Electric Sedan",
            "general": "The Tesla Model 3 is a battery electric mid-size sedan with a range of 358 miles and advanced Autopilot features.",
            "engine": "Electric motor with 283-510 HP, 75-82 kWh battery, 272-358 miles range",
            "features": "15-inch touchscreen, Autopilot, over-the-air updates, Supercharger network access",
            "price": "Starting at $38,990 - $54,990"
        },
        "bmw_3_series": {
            "name": "BMW 3 Series",
            "type": "Luxury Sedan", 
            "general": "The BMW 3 Series is a compact executive car known for sporty handling and luxury features.",
            "engine": "2.0L turbocharged I4 with 255-382 HP, 8-speed automatic transmission",
            "features": "BMW iDrive 8.0, digital cockpit, premium sound system, driver assistance features",
            "price": "Starting at $36,350 - $56,700"
        },
        "honda_civic": {
            "name": "Honda Civic",
            "type": "Compact Sedan",
            "general": "The Honda Civic is a reliable compact sedan known for fuel efficiency and practicality.",
            "engine": "2.0L I4 or 1.5L Turbo I4 with 158-180 HP, excellent fuel economy up to 42 MPG",
            "features": "Honda Sensing safety suite, touchscreen infotainment, wireless Apple CarPlay",
            "price": "Starting at $24,650 - $32,350"
        },
        "ford_f150": {
            "name": "Ford F-150",
            "type": "Full-Size Pickup Truck",
            "general": "The Ford F-150 is America's best-selling truck with best-in-class towing and aluminum body.",
            "engine": "Multiple options: 3.3L V6 to 3.5L EcoBoost V6, 290-450 HP, up to 14,000 lbs towing",
            "features": "Pro Trailer Backup Assist, SYNC 4A, aluminum body, multiple bed lengths",
            "price": "Starting at $37,970 - $76,555"
        }
    }
    
    @staticmethod
    async def get_vehicle_info(vehicle_query: str, info_type: str = "general") -> Dict:
        """Get vehicle information"""
        try:
            # Find vehicle in database
            vehicle_data = None
            for vehicle_id, data in VehicleInfoTools.VEHICLE_DB.items():
                if any(word in vehicle_query.lower() for word in vehicle_id.split('_')):
                    vehicle_data = data
                    break
                elif data["name"].lower() in vehicle_query.lower():
                    vehicle_data = data
                    break
            
            if not vehicle_data:
                available_vehicles = ", ".join([data["name"] for data in VehicleInfoTools.VEHICLE_DB.values()])
                return {
                    "success": True,
                    "message": f"I don't have information about '{vehicle_query}'. I can tell you about: {available_vehicles}"
                }
            
            # Get specific information type
            info = vehicle_data.get(info_type, vehicle_data["general"])
            vehicle_name = vehicle_data["name"]
            
            response = f"📋 {vehicle_name} - {info_type.title()} Information:\n\n{info}"
            
            return {
                "success": True,
                "message": response,
                "vehicle": vehicle_name
            }
            
        except Exception as e:
            return {"success": False, "message": f"Failed to get vehicle info: {e}"}
    
    @staticmethod
    async def list_available_vehicles() -> Dict:
        """List all available vehicles"""
        try:
            vehicles = []
            cars = []
            trucks = []
            
            for vehicle_id, data in VehicleInfoTools.VEHICLE_DB.items():
                vehicle_info = f"- {data['name']}: {data['type']}"
                vehicles.append(vehicle_info)
                
                if "truck" in data["type"].lower():
                    trucks.append(vehicle_info)
                else:
                    cars.append(vehicle_info)
            
            response = "🚗 Available Vehicle Information:\n\n"
            response += "Cars:\n" + "\n".join(cars) + "\n\n"
            response += "Trucks:\n" + "\n".join(trucks) + "\n\n"
            response += "Ask me about any vehicle! For example: 'Tell me about the Tesla Model 3' or 'What are the features of the BMW 3 Series?'"
            
            return {
                "success": True,
                "message": response,
                "vehicles": list(VehicleInfoTools.VEHICLE_DB.values())
            }
            
        except Exception as e:
            return {"success": False, "message": f"Failed to list vehicles: {e}"}
    
    @staticmethod
    async def compare_vehicles(vehicle1: str, vehicle2: str) -> Dict:
        """Compare two vehicles"""
        try:
            # Simple comparison logic
            return {
                "success": True,
                "message": f"Comparison between {vehicle1} and {vehicle2}: Both are excellent vehicles with different strengths. {vehicle1} offers unique advantages, while {vehicle2} excels in other areas."
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to compare vehicles: {e}"}
    
    @staticmethod
    async def search_vehicle_by_criteria(criteria: str) -> Dict:
        """Search vehicles by criteria"""
        try:
            criteria_lower = criteria.lower()
            
            if "electric" in criteria_lower:
                return await VehicleInfoTools.get_vehicle_info("tesla model 3")
            elif "luxury" in criteria_lower:
                return await VehicleInfoTools.get_vehicle_info("bmw 3 series")
            elif "reliable" in criteria_lower or "fuel efficient" in criteria_lower:
                return await VehicleInfoTools.get_vehicle_info("honda civic")
            elif "truck" in criteria_lower:
                return await VehicleInfoTools.get_vehicle_info("ford f150")
            else:
                return {
                    "success": True,
                    "message": "I can help you find vehicles based on criteria like: electric, luxury, reliable, fuel efficient, or truck capabilities."
                }
                
        except Exception as e:
            return {"success": False, "message": f"Failed to search by criteria: {e}"}

# Initialize music system
def initialize_music_system():
    """Initialize music system and load real music files"""
    music_dir = "data/music"
    os.makedirs(music_dir, exist_ok=True)
    
    try:
        # Initialize pygame mixer with better settings for music
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        
        # Find actual music files
        import glob
        supported_extensions = ['*.mp3', '*.wav', '*.ogg', '*.m4a']
        music_files = []
        
        for ext in supported_extensions:
            files = glob.glob(os.path.join(music_dir, ext))
            music_files.extend(files)
        
        if music_files:
            # Use real filenames
            playlist = [os.path.basename(f) for f in music_files]
            VEHICLE_STATE["music"]["playlist"] = playlist
            VEHICLE_STATE["music"]["current_track"] = playlist[0]
            logger.info(f"🎵 Real music system initialized with {len(playlist)} files: {playlist}")
        else:
            # Fallback if no files found
            VEHICLE_STATE["music"]["playlist"] = ["No music files found"]
            VEHICLE_STATE["music"]["current_track"] = "Add music files to data/music/"
            logger.warning(f"🎵 No music files found in {music_dir}")
            
    except Exception as e:
        logger.error(f"🎵 Music system initialization failed: {e}")
        # Fallback playlist
        VEHICLE_STATE["music"]["playlist"] = ["Music system error"]
        VEHICLE_STATE["music"]["current_track"] = "Music system error"

# Initialize on import
initialize_music_system()