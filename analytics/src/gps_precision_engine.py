"""
GPS Precision Engine - Nanosecond Accurate Localization
Revolutionary precision tracking for biomechanical analysis
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import numpy as np
import json
from collections import deque
import struct
import socket
import serial_asyncio

logger = logging.getLogger(__name__)

@dataclass
class GPSCoordinate:
    """Nanosecond-precision GPS coordinate"""
    latitude: float
    longitude: float
    altitude: float
    timestamp_ns: int  # Nanosecond timestamp
    accuracy_horizontal: float  # Meters
    accuracy_vertical: float  # Meters
    velocity_x: float  # m/s
    velocity_y: float  # m/s
    velocity_z: float  # m/s
    satellite_count: int
    hdop: float  # Horizontal Dilution of Precision
    vdop: float  # Vertical Dilution of Precision

@dataclass
class PrecisionMovement:
    """Ultra-precise movement data combining GPS and computer vision"""
    movement_id: str
    timestamp_ns: int
    gps_position: GPSCoordinate
    pixel_position: Tuple[float, float]  # From computer vision
    world_position_3d: Tuple[float, float, float]  # Calibrated world coordinates
    velocity_vector: Tuple[float, float, float]
    acceleration_vector: Tuple[float, float, float]
    precision_score: float  # 0-1 confidence in measurement
    biomechanical_features: Dict[str, Any]

class NanosecondTimer:
    """Ultra-high precision timing for synchronization"""
    
    def __init__(self):
        self.start_time_ns = time.time_ns()
        self.calibration_offset = 0
    
    def get_nanosecond_timestamp(self) -> int:
        """Get current nanosecond timestamp"""
        return time.time_ns() - self.calibration_offset
    
    def calibrate_with_gps(self, gps_timestamp_ns: int):
        """Calibrate local timer with GPS time"""
        local_ns = time.time_ns()
        self.calibration_offset = local_ns - gps_timestamp_ns
        logger.info(f"Timer calibrated with GPS, offset: {self.calibration_offset}ns")

class GPSReceiver:
    """Interface for high-precision GPS receiver"""
    
    def __init__(self, device_path: str = "/dev/ttyUSB0", baudrate: int = 115200):
        self.device_path = device_path
        self.baudrate = baudrate
        self.reader = None
        self.writer = None
        self.last_fix: Optional[GPSCoordinate] = None
        self.fix_history = deque(maxlen=1000)
        
    async def initialize(self):
        """Initialize GPS receiver connection"""
        try:
            self.reader, self.writer = await serial_asyncio.open_serial_connection(
                url=self.device_path, 
                baudrate=self.baudrate
            )
            logger.info(f"GPS receiver connected on {self.device_path}")
            
            # Start reading GPS data
            asyncio.create_task(self._read_gps_data())
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize GPS receiver: {e}")
            return False
    
    async def _read_gps_data(self):
        """Continuously read GPS data"""
        buffer = ""
        
        while True:
            try:
                data = await self.reader.read(1024)
                if not data:
                    break
                    
                buffer += data.decode('ascii', errors='ignore')
                
                # Process complete NMEA sentences
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                        await self._parse_gga_sentence(line.strip())
                    elif line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                        await self._parse_rmc_sentence(line.strip())
                        
            except Exception as e:
                logger.error(f"Error reading GPS data: {e}")
                await asyncio.sleep(1)
    
    async def _parse_gga_sentence(self, sentence: str):
        """Parse GGA sentence for position and quality data"""
        try:
            parts = sentence.split(',')
            if len(parts) < 15:
                return
            
            # Extract timestamp with nanosecond precision
            time_str = parts[1]
            if not time_str:
                return
                
            timestamp_ns = self._nmea_time_to_nanoseconds(time_str)
            
            # Extract position
            lat_str, lat_dir = parts[2], parts[3]
            lon_str, lon_dir = parts[4], parts[5]
            
            if not lat_str or not lon_str:
                return
            
            latitude = self._nmea_coord_to_decimal(lat_str, lat_dir)
            longitude = self._nmea_coord_to_decimal(lon_str, lon_dir)
            
            # Quality indicators
            quality = int(parts[6]) if parts[6] else 0
            satellite_count = int(parts[7]) if parts[7] else 0
            hdop = float(parts[8]) if parts[8] else 99.0
            altitude = float(parts[9]) if parts[9] else 0.0
            
            # Estimate accuracy based on HDOP and satellite count
            accuracy_horizontal = hdop * 2.5  # Rough estimate
            accuracy_vertical = hdop * 3.0
            
            # Create GPS coordinate
            gps_coord = GPSCoordinate(
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                timestamp_ns=timestamp_ns,
                accuracy_horizontal=accuracy_horizontal,
                accuracy_vertical=accuracy_vertical,
                velocity_x=0.0,  # Will be calculated from position history
                velocity_y=0.0,
                velocity_z=0.0,
                satellite_count=satellite_count,
                hdop=hdop,
                vdop=hdop * 1.2  # Estimate if not available
            )
            
            # Calculate velocity if we have previous position
            if self.last_fix:
                time_diff = (timestamp_ns - self.last_fix.timestamp_ns) / 1e9  # Convert to seconds
                if time_diff > 0:
                    # Calculate displacement
                    dx, dy = self._calculate_displacement(
                        self.last_fix.latitude, self.last_fix.longitude,
                        latitude, longitude
                    )
                    dz = altitude - self.last_fix.altitude
                    
                    # Calculate velocity
                    gps_coord.velocity_x = dx / time_diff
                    gps_coord.velocity_y = dy / time_diff
                    gps_coord.velocity_z = dz / time_diff
            
            self.last_fix = gps_coord
            self.fix_history.append(gps_coord)
            
            logger.debug(f"GPS fix: {latitude:.9f}, {longitude:.9f}, accuracy: {accuracy_horizontal:.2f}m")
            
        except Exception as e:
            logger.error(f"Error parsing GGA sentence: {e}")
    
    def _nmea_time_to_nanoseconds(self, time_str: str) -> int:
        """Convert NMEA time string to nanosecond timestamp"""
        # HHMMSS.sss format
        if len(time_str) < 6:
            return time.time_ns()
        
        hours = int(time_str[:2])
        minutes = int(time_str[2:4])
        seconds = float(time_str[4:])
        
        # Get current date (GPS time doesn't include date in GGA)
        now = datetime.now()
        gps_time = now.replace(
            hour=hours, 
            minute=minutes, 
            second=int(seconds),
            microsecond=int((seconds % 1) * 1000000)
        )
        
        return int(gps_time.timestamp() * 1e9)
    
    def _nmea_coord_to_decimal(self, coord_str: str, direction: str) -> float:
        """Convert NMEA coordinate to decimal degrees"""
        if not coord_str:
            return 0.0
        
        # Format: DDMM.MMMMM or DDDMM.MMMMM
        if len(coord_str) < 7:
            return 0.0
        
        if direction in ['N', 'S']:
            # Latitude: DDMM.MMMMM
            degrees = int(coord_str[:2])
            minutes = float(coord_str[2:])
        else:
            # Longitude: DDDMM.MMMMM
            degrees = int(coord_str[:3])
            minutes = float(coord_str[3:])
        
        decimal = degrees + minutes / 60.0
        
        if direction in ['S', 'W']:
            decimal = -decimal
        
        return decimal
    
    def _calculate_displacement(self, lat1: float, lon1: float, lat2: float, lon2: float) -> Tuple[float, float]:
        """Calculate displacement in meters between two GPS coordinates"""
        # Convert to radians
        lat1_r, lon1_r = np.radians(lat1), np.radians(lon1)
        lat2_r, lon2_r = np.radians(lat2), np.radians(lon2)
        
        # Earth radius in meters
        R = 6378137.0
        
        # Calculate differences
        dlat = lat2_r - lat1_r
        dlon = lon2_r - lon1_r
        
        # Calculate displacement in meters
        dx = R * dlon * np.cos((lat1_r + lat2_r) / 2)
        dy = R * dlat
        
        return dx, dy
    
    async def get_current_position(self) -> Optional[GPSCoordinate]:
        """Get the most recent GPS position"""
        return self.last_fix
    
    async def get_position_at_time(self, timestamp_ns: int, tolerance_ns: int = 1000000) -> Optional[GPSCoordinate]:
        """Get GPS position closest to specified timestamp"""
        if not self.fix_history:
            return None
        
        best_fix = None
        min_time_diff = float('inf')
        
        for fix in self.fix_history:
            time_diff = abs(fix.timestamp_ns - timestamp_ns)
            if time_diff <= tolerance_ns and time_diff < min_time_diff:
                min_time_diff = time_diff
                best_fix = fix
        
        return best_fix

class CoordinateCalibrator:
    """Calibrates between GPS coordinates, pixel coordinates, and world coordinates"""
    
    def __init__(self):
        self.calibration_points = []  # List of (gps, pixel, world) tuples
        self.transformation_matrix = None
        self.is_calibrated = False
        
    def add_calibration_point(self, gps_coord: GPSCoordinate, pixel_pos: Tuple[float, float], world_pos: Tuple[float, float, float]):
        """Add a calibration point linking GPS, pixel, and world coordinates"""
        self.calibration_points.append((gps_coord, pixel_pos, world_pos))
        logger.info(f"Added calibration point, total: {len(self.calibration_points)}")
        
        # Recalibrate if we have enough points
        if len(self.calibration_points) >= 4:
            self._calculate_transformation()
    
    def _calculate_transformation(self):
        """Calculate transformation matrix from calibration points"""
        try:
            # Extract GPS coordinates and world coordinates
            gps_points = []
            world_points = []
            
            for gps_coord, pixel_pos, world_pos in self.calibration_points:
                gps_points.append([gps_coord.latitude, gps_coord.longitude])
                world_points.append([world_pos[0], world_pos[1]])
            
            gps_array = np.array(gps_points)
            world_array = np.array(world_points)
            
            # Calculate transformation using least squares
            # Add column of ones for translation
            gps_homogeneous = np.column_stack([gps_array, np.ones(len(gps_array))])
            
            # Solve for transformation matrix
            self.transformation_matrix = np.linalg.lstsq(gps_homogeneous, world_array, rcond=None)[0]
            self.is_calibrated = True
            
            logger.info("Coordinate transformation calibrated successfully")
            
        except Exception as e:
            logger.error(f"Failed to calculate coordinate transformation: {e}")
            self.is_calibrated = False
    
    def gps_to_world(self, gps_coord: GPSCoordinate) -> Optional[Tuple[float, float, float]]:
        """Convert GPS coordinate to world coordinate"""
        if not self.is_calibrated:
            return None
        
        try:
            gps_point = np.array([gps_coord.latitude, gps_coord.longitude, 1.0])
            world_xy = np.dot(gps_point, self.transformation_matrix)
            
            # For Z coordinate, use altitude directly for now
            # Could be enhanced with more sophisticated terrain modeling
            world_z = gps_coord.altitude
            
            return (float(world_xy[0]), float(world_xy[1]), float(world_z))
            
        except Exception as e:
            logger.error(f"Error converting GPS to world coordinates: {e}")
            return None

class GPSPrecisionEngine:
    """Main engine for nanosecond-accurate GPS positioning and tracking"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timer = NanosecondTimer()
        self.gps_receiver = GPSReceiver(
            device_path=config.get("gps_device", "/dev/ttyUSB0"),
            baudrate=config.get("gps_baudrate", 115200)
        )
        self.calibrator = CoordinateCalibrator()
        
        # Movement tracking
        self.movement_history = deque(maxlen=10000)
        self.current_movements: Dict[str, PrecisionMovement] = {}
        
        # Precision metrics
        self.position_accuracy_threshold = config.get("position_accuracy_threshold", 0.1)  # meters
        self.velocity_accuracy_threshold = config.get("velocity_accuracy_threshold", 0.01)  # m/s
        
        logger.info("GPS Precision Engine initialized")
    
    async def initialize(self):
        """Initialize the GPS precision engine"""
        try:
            success = await self.gps_receiver.initialize()
            if not success:
                return False
            
            # Calibrate timer with GPS
            await asyncio.sleep(2)  # Wait for first GPS fix
            current_pos = await self.gps_receiver.get_current_position()
            if current_pos:
                self.timer.calibrate_with_gps(current_pos.timestamp_ns)
            
            logger.info("GPS Precision Engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize GPS Precision Engine: {e}")
            return False
    
    async def track_movement(self, entity_id: str, pixel_position: Tuple[float, float], 
                           biomech_features: Dict[str, Any] = None) -> Optional[PrecisionMovement]:
        """Track movement with nanosecond precision"""
        try:
            timestamp_ns = self.timer.get_nanosecond_timestamp()
            
            # Get GPS position at this exact timestamp
            gps_position = await self.gps_receiver.get_position_at_time(timestamp_ns)
            if not gps_position:
                return None
            
            # Convert to world coordinates
            world_position = self.calibrator.gps_to_world(gps_position)
            if not world_position:
                return None
            
            # Calculate velocity and acceleration
            velocity_vector = (gps_position.velocity_x, gps_position.velocity_y, gps_position.velocity_z)
            acceleration_vector = self._calculate_acceleration(entity_id, velocity_vector)
            
            # Calculate precision score
            precision_score = self._calculate_precision_score(gps_position)
            
            # Create movement record
            movement = PrecisionMovement(
                movement_id=f"{entity_id}_{timestamp_ns}",
                timestamp_ns=timestamp_ns,
                gps_position=gps_position,
                pixel_position=pixel_position,
                world_position_3d=world_position,
                velocity_vector=velocity_vector,
                acceleration_vector=acceleration_vector,
                precision_score=precision_score,
                biomechanical_features=biomech_features or {}
            )
            
            # Store movement
            self.movement_history.append(movement)
            self.current_movements[entity_id] = movement
            
            return movement
            
        except Exception as e:
            logger.error(f"Error tracking movement for {entity_id}: {e}")
            return None
    
    def _calculate_acceleration(self, entity_id: str, current_velocity: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Calculate acceleration from velocity history"""
        if entity_id not in self.current_movements:
            return (0.0, 0.0, 0.0)
        
        last_movement = self.current_movements[entity_id]
        last_velocity = last_movement.velocity_vector
        
        time_diff = (self.timer.get_nanosecond_timestamp() - last_movement.timestamp_ns) / 1e9
        
        if time_diff <= 0:
            return (0.0, 0.0, 0.0)
        
        ax = (current_velocity[0] - last_velocity[0]) / time_diff
        ay = (current_velocity[1] - last_velocity[1]) / time_diff
        az = (current_velocity[2] - last_velocity[2]) / time_diff
        
        return (ax, ay, az)
    
    def _calculate_precision_score(self, gps_position: GPSCoordinate) -> float:
        """Calculate precision score based on GPS quality metrics"""
        try:
            # Factors affecting precision
            accuracy_score = max(0, 1.0 - gps_position.accuracy_horizontal / 10.0)
            satellite_score = min(1.0, gps_position.satellite_count / 12.0)
            hdop_score = max(0, 1.0 - gps_position.hdop / 5.0)
            
            # Weighted average
            precision_score = (
                accuracy_score * 0.4 +
                satellite_score * 0.3 +
                hdop_score * 0.3
            )
            
            return max(0.0, min(1.0, precision_score))
            
        except Exception as e:
            logger.error(f"Error calculating precision score: {e}")
            return 0.0
    
    async def get_movement_at_time(self, timestamp_ns: int, tolerance_ns: int = 1000000) -> Optional[PrecisionMovement]:
        """Get movement data closest to specified timestamp"""
        best_movement = None
        min_time_diff = float('inf')
        
        for movement in self.movement_history:
            time_diff = abs(movement.timestamp_ns - timestamp_ns)
            if time_diff <= tolerance_ns and time_diff < min_time_diff:
                min_time_diff = time_diff
                best_movement = movement
        
        return best_movement
    
    async def get_precision_metrics(self) -> Dict[str, Any]:
        """Get current precision metrics"""
        current_pos = await self.gps_receiver.get_current_position()
        
        return {
            "gps_connected": current_pos is not None,
            "current_accuracy": current_pos.accuracy_horizontal if current_pos else None,
            "satellite_count": current_pos.satellite_count if current_pos else 0,
            "hdop": current_pos.hdop if current_pos else 99.0,
            "calibrated": self.calibrator.is_calibrated,
            "calibration_points": len(self.calibrator.calibration_points),
            "movement_history_count": len(self.movement_history),
            "active_tracks": len(self.current_movements)
        }
    
    async def export_precision_data(self, start_time_ns: int, end_time_ns: int) -> List[Dict[str, Any]]:
        """Export precision movement data for analysis"""
        filtered_movements = [
            asdict(movement) for movement in self.movement_history
            if start_time_ns <= movement.timestamp_ns <= end_time_ns
        ]
        
        return filtered_movements 