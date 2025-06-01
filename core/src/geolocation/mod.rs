pub mod kalman;
pub mod triangulation;
pub mod verification;
pub mod precision_timing;

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeolocationPoint {
    pub latitude: f64,
    pub longitude: f64,
    pub altitude: Option<f64>,
    pub accuracy: f64,
    pub timestamp_ns: u128,  // Nanosecond precision
    pub source: String,
    pub confidence: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CellTowerData {
    pub tower_id: String,
    pub latitude: f64,
    pub longitude: f64,
    pub signal_strength: f64,  // dBm
    pub distance_estimate: Option<f64>,
    pub timestamp_ns: u128,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WiFiAccessPoint {
    pub bssid: String,
    pub ssid: Option<String>,
    pub latitude: f64,
    pub longitude: f64,
    pub signal_strength: f64,
    pub frequency: Option<f64>,
    pub timestamp_ns: u128,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocationVerification {
    pub verification_id: String,
    pub user_id: String,
    pub session_id: String,
    pub location: GeolocationPoint,
    pub verification_method: VerificationMethod,
    pub confidence_score: f64,
    pub exclusion_zones: Vec<ExclusionZone>,
    pub is_excluded: bool,
    pub timestamp_ns: u128,
    pub video_frame_hash: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VerificationMethod {
    GPS,
    CellTower,
    WiFi,
    Hybrid,
    VideoAnalysis,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExclusionZone {
    pub zone_id: String,
    pub center_lat: f64,
    pub center_lon: f64,
    pub radius_meters: f64,
    pub zone_type: ExclusionType,
    pub active_from: DateTime<Utc>,
    pub active_until: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ExclusionType {
    EventLocation,    // Where the event is happening
    RestrictedRegion, // Legal restrictions
    VenueProximity,   // Near the venue
    CompetitorZone,   // Areas where competitors are located
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransactionVerification {
    pub transaction_id: String,
    pub user_id: String,
    pub location_verification: LocationVerification,
    pub transaction_timestamp_ns: u128,
    pub video_evidence: VideoEvidence,
    pub cryptographic_proof: String,
    pub blockchain_hash: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VideoEvidence {
    pub frame_hash: String,
    pub timestamp_ns: u128,
    pub frame_metadata: FrameMetadata,
    pub location_markers: Vec<LocationMarker>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FrameMetadata {
    pub camera_id: String,
    pub resolution: (u32, u32),
    pub fps: f64,
    pub encoding: String,
    pub checksum: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocationMarker {
    pub marker_type: String,
    pub coordinates: (f64, f64),  // Pixel coordinates in frame
    pub confidence: f64,
    pub reference_location: Option<GeolocationPoint>,
}

pub struct GeolocationService {
    kalman_filter: Arc<kalman::KalmanFilter>,
    triangulation_engine: Arc<triangulation::TriangulationEngine>,
    verification_engine: Arc<verification::VerificationEngine>,
    precision_timer: Arc<precision_timing::PrecisionTimer>,
    
    // Real-time location tracking
    active_sessions: Arc<RwLock<HashMap<String, LocationSession>>>,
    exclusion_zones: Arc<RwLock<Vec<ExclusionZone>>>,
    verification_history: Arc<RwLock<HashMap<String, Vec<LocationVerification>>>>,
    
    // Video frame correlation
    frame_location_map: Arc<RwLock<HashMap<String, GeolocationPoint>>>,
    transaction_evidence: Arc<RwLock<HashMap<String, TransactionVerification>>>,
}

#[derive(Debug, Clone)]
struct LocationSession {
    session_id: String,
    user_id: String,
    start_time: u128,
    last_update: u128,
    location_history: Vec<GeolocationPoint>,
    current_exclusion_status: bool,
}

impl GeolocationService {
    pub async fn new() -> Self {
        Self {
            kalman_filter: Arc::new(kalman::KalmanFilter::new()),
            triangulation_engine: Arc::new(triangulation::TriangulationEngine::new()),
            verification_engine: Arc::new(verification::VerificationEngine::new()),
            precision_timer: Arc::new(precision_timing::PrecisionTimer::new()),
            
            active_sessions: Arc::new(RwLock::new(HashMap::new())),
            exclusion_zones: Arc::new(RwLock::new(Vec::new())),
            verification_history: Arc::new(RwLock::new(HashMap::new())),
            
            frame_location_map: Arc::new(RwLock::new(HashMap::new())),
            transaction_evidence: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    pub async fn start_location_session(&self, user_id: String) -> String {
        let session_id = uuid::Uuid::new_v4().to_string();
        let timestamp_ns = self.precision_timer.get_nanosecond_timestamp().await;
        
        let session = LocationSession {
            session_id: session_id.clone(),
            user_id,
            start_time: timestamp_ns,
            last_update: timestamp_ns,
            location_history: Vec::new(),
            current_exclusion_status: false,
        };
        
        let mut sessions = self.active_sessions.write().await;
        sessions.insert(session_id.clone(), session);
        
        session_id
    }
    
    pub async fn update_location_multi_source(
        &self,
        session_id: &str,
        gps_data: Option<GeolocationPoint>,
        cell_towers: Vec<CellTowerData>,
        wifi_points: Vec<WiFiAccessPoint>,
        video_frame_hash: Option<String>
    ) -> Result<LocationVerification, Box<dyn std::error::Error + Send + Sync>> {
        let timestamp_ns = self.precision_timer.get_nanosecond_timestamp().await;
        
        // Multi-source data fusion
        let fused_location = self.fuse_location_sources(
            gps_data,
            &cell_towers,
            &wifi_points,
            timestamp_ns
        ).await?;
        
        // Apply Kalman filtering for smoothing
        let filtered_location = self.kalman_filter.filter_location(
            &fused_location,
            &self.get_session_history(session_id).await
        ).await;
        
        // Create verification
        let verification = self.create_location_verification(
            session_id,
            filtered_location,
            video_frame_hash,
            timestamp_ns
        ).await?;
        
        // Update session
        self.update_session(&verification).await;
        
        // Store frame-location correlation if video provided
        if let Some(frame_hash) = &verification.video_frame_hash {
            self.correlate_frame_location(frame_hash.clone(), verification.location.clone()).await;
        }
        
        Ok(verification)
    }
    
    async fn fuse_location_sources(
        &self,
        gps_data: Option<GeolocationPoint>,
        cell_towers: &[CellTowerData],
        wifi_points: &[WiFiAccessPoint],
        timestamp_ns: u128
    ) -> Result<GeolocationPoint, Box<dyn std::error::Error + Send + Sync>> {
        let mut weighted_locations = Vec::new();
        
        // GPS data (highest accuracy when available)
        if let Some(gps) = gps_data {
            weighted_locations.push((gps, 1.0 / (1.0 + gps.accuracy)));
        }
        
        // Cell tower triangulation
        if !cell_towers.is_empty() {
            let triangulated = self.triangulation_engine.triangulate_cell_towers(cell_towers).await?;
            weighted_locations.push((triangulated, 0.6));
        }
        
        // WiFi triangulation
        if !wifi_points.is_empty() {
            let wifi_location = self.triangulation_engine.triangulate_wifi(wifi_points).await?;
            weighted_locations.push((wifi_location, 0.8));
        }
        
        // Weighted average of all sources
        self.calculate_weighted_location(weighted_locations, timestamp_ns).await
    }
    
    async fn calculate_weighted_location(
        &self,
        weighted_locations: Vec<(GeolocationPoint, f64)>,
        timestamp_ns: u128
    ) -> Result<GeolocationPoint, Box<dyn std::error::Error + Send + Sync>> {
        if weighted_locations.is_empty() {
            return Err("No location sources available".into());
        }
        
        let total_weight: f64 = weighted_locations.iter().map(|(_, w)| w).sum();
        
        let weighted_lat: f64 = weighted_locations.iter()
            .map(|(loc, w)| loc.latitude * w)
            .sum::<f64>() / total_weight;
            
        let weighted_lon: f64 = weighted_locations.iter()
            .map(|(loc, w)| loc.longitude * w)
            .sum::<f64>() / total_weight;
            
        let weighted_accuracy: f64 = weighted_locations.iter()
            .map(|(loc, w)| loc.accuracy * w)
            .sum::<f64>() / total_weight;
            
        let confidence: f64 = weighted_locations.iter()
            .map(|(loc, w)| loc.confidence * w)
            .sum::<f64>() / total_weight;
        
        Ok(GeolocationPoint {
            latitude: weighted_lat,
            longitude: weighted_lon,
            altitude: None,
            accuracy: weighted_accuracy,
            timestamp_ns,
            source: "fused_multi_source".to_string(),
            confidence,
        })
    }
    
    async fn create_location_verification(
        &self,
        session_id: &str,
        location: GeolocationPoint,
        video_frame_hash: Option<String>,
        timestamp_ns: u128
    ) -> Result<LocationVerification, Box<dyn std::error::Error + Send + Sync>> {
        let sessions = self.active_sessions.read().await;
        let session = sessions.get(session_id)
            .ok_or("Session not found")?;
        
        let verification_id = uuid::Uuid::new_v4().to_string();
        
        // Check exclusion zones
        let exclusion_zones = self.exclusion_zones.read().await;
        let is_excluded = self.check_exclusion_zones(&location, &exclusion_zones).await;
        
        // Calculate confidence score
        let confidence_score = self.verification_engine.calculate_confidence(
            &location,
            &session.location_history,
            is_excluded
        ).await;
        
        Ok(LocationVerification {
            verification_id,
            user_id: session.user_id.clone(),
            session_id: session_id.to_string(),
            location,
            verification_method: VerificationMethod::Hybrid,
            confidence_score,
            exclusion_zones: exclusion_zones.clone(),
            is_excluded,
            timestamp_ns,
            video_frame_hash,
        })
    }
    
    async fn check_exclusion_zones(
        &self,
        location: &GeolocationPoint,
        exclusion_zones: &[ExclusionZone]
    ) -> bool {
        for zone in exclusion_zones {
            let distance = self.calculate_distance(
                location.latitude,
                location.longitude,
                zone.center_lat,
                zone.center_lon
            );
            
            if distance <= zone.radius_meters {
                return true;
            }
        }
        false
    }
    
    fn calculate_distance(&self, lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
        // Haversine formula for distance calculation
        let r = 6371000.0; // Earth's radius in meters
        let d_lat = (lat2 - lat1).to_radians();
        let d_lon = (lon2 - lon1).to_radians();
        let lat1_rad = lat1.to_radians();
        let lat2_rad = lat2.to_radians();
        
        let a = (d_lat / 2.0).sin().powi(2) + 
                lat1_rad.cos() * lat2_rad.cos() * (d_lon / 2.0).sin().powi(2);
        let c = 2.0 * a.sqrt().atan2((1.0 - a).sqrt());
        
        r * c
    }
    
    async fn update_session(&self, verification: &LocationVerification) {
        let mut sessions = self.active_sessions.write().await;
        if let Some(session) = sessions.get_mut(&verification.session_id) {
            session.last_update = verification.timestamp_ns;
            session.location_history.push(verification.location.clone());
            session.current_exclusion_status = verification.is_excluded;
            
            // Keep history manageable
            if session.location_history.len() > 1000 {
                session.location_history.remove(0);
            }
        }
        
        // Store in verification history
        let mut history = self.verification_history.write().await;
        history.entry(verification.user_id.clone())
            .or_insert_with(Vec::new)
            .push(verification.clone());
    }
    
    async fn get_session_history(&self, session_id: &str) -> Vec<GeolocationPoint> {
        let sessions = self.active_sessions.read().await;
        sessions.get(session_id)
            .map(|s| s.location_history.clone())
            .unwrap_or_default()
    }
    
    async fn correlate_frame_location(&self, frame_hash: String, location: GeolocationPoint) {
        let mut frame_map = self.frame_location_map.write().await;
        frame_map.insert(frame_hash, location);
    }
    
    pub async fn create_transaction_verification(
        &self,
        transaction_id: String,
        user_id: String,
        video_evidence: VideoEvidence
    ) -> Result<TransactionVerification, Box<dyn std::error::Error + Send + Sync>> {
        let timestamp_ns = self.precision_timer.get_nanosecond_timestamp().await;
        
        // Get location from frame correlation
        let frame_map = self.frame_location_map.read().await;
        let frame_location = frame_map.get(&video_evidence.frame_hash)
            .ok_or("Frame location not found")?;
        
        // Create location verification for this transaction
        let location_verification = LocationVerification {
            verification_id: uuid::Uuid::new_v4().to_string(),
            user_id: user_id.clone(),
            session_id: format!("tx_{}", transaction_id),
            location: frame_location.clone(),
            verification_method: VerificationMethod::VideoAnalysis,
            confidence_score: 0.95, // High confidence from video evidence
            exclusion_zones: self.exclusion_zones.read().await.clone(),
            is_excluded: self.check_exclusion_zones(frame_location, &self.exclusion_zones.read().await).await,
            timestamp_ns,
            video_frame_hash: Some(video_evidence.frame_hash.clone()),
        };
        
        // Generate cryptographic proof
        let cryptographic_proof = self.generate_cryptographic_proof(
            &transaction_id,
            &user_id,
            &location_verification,
            &video_evidence
        ).await;
        
        let verification = TransactionVerification {
            transaction_id,
            user_id,
            location_verification,
            transaction_timestamp_ns: timestamp_ns,
            video_evidence,
            cryptographic_proof,
            blockchain_hash: None, // Would be set when recorded on blockchain
        };
        
        // Store transaction evidence
        let mut evidence = self.transaction_evidence.write().await;
        evidence.insert(verification.transaction_id.clone(), verification.clone());
        
        Ok(verification)
    }
    
    async fn generate_cryptographic_proof(
        &self,
        transaction_id: &str,
        user_id: &str,
        location_verification: &LocationVerification,
        video_evidence: &VideoEvidence
    ) -> String {
        // Generate a cryptographic proof combining all elements
        let proof_data = format!(
            "{}:{}:{}:{}:{}",
            transaction_id,
            user_id,
            location_verification.timestamp_ns,
            location_verification.location.latitude,
            video_evidence.frame_hash
        );
        
        // In real implementation, this would use proper cryptographic signatures
        format!("proof_{}", sha256::digest(proof_data))
    }
    
    pub async fn add_exclusion_zone(&self, zone: ExclusionZone) {
        let mut zones = self.exclusion_zones.write().await;
        zones.push(zone);
    }
    
    pub async fn verify_transaction_location(&self, transaction_id: &str) -> Option<bool> {
        let evidence = self.transaction_evidence.read().await;
        evidence.get(transaction_id)
            .map(|tx| !tx.location_verification.is_excluded)
    }
    
    pub async fn get_location_history(&self, user_id: &str) -> Vec<LocationVerification> {
        let history = self.verification_history.read().await;
        history.get(user_id).cloned().unwrap_or_default()
    }
    
    pub async fn is_user_excluded(&self, user_id: &str) -> bool {
        let sessions = self.active_sessions.read().await;
        sessions.values()
            .any(|session| session.user_id == user_id && session.current_exclusion_status)
    }
    
    pub async fn get_nanosecond_timestamp(&self) -> u128 {
        self.precision_timer.get_nanosecond_timestamp().await
    }
} 