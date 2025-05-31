---
layout: page
title: Computer Vision Deep Dive
nav_order: 3
---

<div class="page-logo">
  <img src="assets/Morphine2DCSDS.svg" alt="Morphine Chemical Structure" class="page-logo-img">
</div>

# Computer Vision Deep Dive
{: .no_toc}

## Table of contents
{: .no_toc .text-delta}

1. TOC
{:toc}

---

## Overview

The Morphine Platform's computer vision capabilities are powered by two specialized frameworks: **Vibrio** for general human motion analysis and **Moriarty** for sports-specific biomechanical analysis. Together, they provide comprehensive real-time video analysis that drives the platform's analytics and micro-betting features.

## Framework Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Morphine CV Pipeline                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │     Vibrio      │              │    Moriarty     │          │
│  │ Motion Analysis │              │ Sports Analysis │          │
│  └─────────┬───────┘              └─────────┬───────┘          │
│            │                                │                  │
│            └────────────┬───────────────────┘                  │
│                         │                                      │
│                         ▼                                      │
│               ┌─────────────────┐                              │
│               │ Analytics Fusion│                              │
│               │    & Output     │                              │
│               └─────────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

## Vibrio Framework

### Purpose & Capabilities

Vibrio is designed for general human motion analysis with a focus on speed estimation, tracking, and optical analysis. It excels at processing live streams and providing real-time insights.

**Key Features:**
- Human detection using YOLOv8
- Multi-object tracking with Kalman filters
- Speed estimation and physics verification
- Advanced optical flow analysis
- Neuromorphic camera simulation

### Technical Architecture

```
┌───────────────┐      ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  Human        │      │  Object       │      │  Speed        │      │  Physics      │
│  Detection    ├─────►│  Tracking     ├─────►│  Estimation   ├─────►│  Verification │
└───────────────┘      └───────────────┘      └───────────────┘      └───────────────┘
                                                                             │
        ┌────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  Optical      │      │  Pose         │      │  Result       │
│  Analysis     │◄─────┤  Detection    │      │  Visualization│
└───────────────┘      └───────────────┘      └───────────────┘
```

### Core Components

#### 1. Human Detection

```python
class HumanDetector:
    def __init__(self, model_path="yolov8n.pt", conf_threshold=0.5):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        results = self.model(frame, conf=self.conf_threshold)
        return self.parse_detections(results)
```

**Performance Specifications:**
- **Model**: YOLOv8 nano to large variants
- **Speed**: 30-100 FPS depending on hardware
- **Accuracy**: >95% precision on human detection
- **Latency**: <20ms per frame on GPU

#### 2. Object Tracking

Uses Kalman filtering with Hungarian algorithm for assignment:

**State Vector:**
$$x = [c_x, c_y, w, h, \dot{c_x}, \dot{c_y}, \dot{s}]^T$$

Where:
- $c_x, c_y$ are center coordinates
- $w, h$ are bounding box dimensions
- $\dot{c_x}, \dot{c_y}$ are velocity components
- $\dot{s}$ is scale change rate

```python
class HumanTracker:
    def __init__(self, max_age=30, min_hits=3, iou_threshold=0.3):
        self.kalman_filters = []
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
    
    def update(self, detections: List[Detection], frame_idx: int) -> List[Track]:
        # Hungarian algorithm for detection-track assignment
        matched, unmatched_dets, unmatched_trks = self.associate_detections_to_trackers(
            detections, self.trackers, self.iou_threshold
        )
        
        # Update matched trackers with assigned detections
        for m in matched:
            self.trackers[m[1]].update(detections[m[0]])
        
        return self.get_active_tracks()
```

#### 3. Speed Estimation

**Mathematical Foundation:**

$$v = \frac{\Delta d}{\Delta t} = \frac{d_{pixels} \cdot r_{calibration}}{\Delta frames / fps}$$

```python
class SpeedEstimator:
    def __init__(self, calibration=None, smoothing_window=5):
        self.calibration = calibration or self.default_calibration()
        self.smoothing_window = smoothing_window
    
    def estimate(self, tracks: List[Track], frame_idx: int, fps: float) -> List[Track]:
        for track in tracks:
            if len(track.history) >= 2:
                # Calculate displacement
                displacement = self.calculate_displacement(track.history[-2:])
                
                # Convert to real-world speed
                speed_ms = (displacement * self.calibration) / (1.0 / fps)
                speed_kmh = speed_ms * 3.6
                
                # Apply smoothing
                track.speeds.append(speed_kmh)
                track.current_speed = self.smooth_speed(track.speeds)
        
        return tracks
```

#### 4. Optical Analysis

**Advanced Methods:**

1. **Optical Flow Analysis** - Farneback dense optical flow
2. **Motion Energy Analysis** - Motion History Images (MHI)
3. **Neuromorphic Simulation** - Event-based detection
4. **Texture Analysis** - Gabor filters and LBP

```python
class OpticalAnalyzer:
    def __init__(self, methods=['optical_flow', 'motion_energy']):
        self.methods = methods
        self.flow_params = dict(
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2
        )
    
    def analyze_frame(self, frame: np.ndarray, prev_frame: np.ndarray) -> Dict[str, Any]:
        results = {}
        
        if 'optical_flow' in self.methods:
            flow = cv2.calcOpticalFlowPyrLK(prev_frame, frame, **self.flow_params)
            results['optical_flow'] = self.analyze_flow(flow)
        
        if 'motion_energy' in self.methods:
            mhi = self.create_motion_history_image(frame, prev_frame)
            results['motion_energy'] = self.analyze_motion_energy(mhi)
        
        return results
```

## Moriarty Framework

### Purpose & Capabilities

Moriarty specializes in sports video analysis with biomechanical precision. It provides detailed pose estimation, stride analysis, and performance metrics specifically designed for athletic analysis.

**Key Features:**
- MediaPipe BlazePose integration (33-point skeleton)
- Biomechanical analysis with joint angles and velocities
- Stride analysis and gait detection
- Ground reaction force estimation
- Distributed processing for batch analysis

### Technical Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Video Input   │    │  Pose Analysis  │    │  Biomechanics   │
│                 ├───►│                 ├───►│                 │
│ - Frame Extract │    │ - Human Detect  │    │ - Kinematics    │
│ - Preprocessing │    │ - Pose Estimate │    │ - Dynamics      │
└─────────────────┘    │ - Skeleton Track│    │ - Force Estim   │
                       └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐           │
│  Visualization  │    │  Distributed    │           │
│                 │◄───┤  Processing     │◄──────────┘
│ - Overlay       │    │                 │
│ - Annotations   │    │ - Ray/Dask      │
└─────────────────┘    │ - Memory Mgmt   │
                       └─────────────────┘
```

### Core Components

#### 1. Pose Analysis

```python
class PoseAnalyzer:
    def __init__(self, complexity=1):
        self.pose_detector = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=complexity,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.human_detector = YOLO('yolov8n.pt')
    
    def analyze_frame(self, frame: np.ndarray) -> PoseResult:
        # Detect humans first
        detections = self.human_detector(frame)
        
        poses = []
        for detection in detections:
            # Extract person region
            person_roi = self.extract_roi(frame, detection.bbox)
            
            # Estimate pose
            results = self.pose_detector.process(person_roi)
            if results.pose_landmarks:
                pose = self.extract_pose_data(results.pose_landmarks)
                poses.append(pose)
        
        return PoseResult(poses=poses, frame_idx=self.frame_count)
```

#### 2. Biomechanical Analysis

**Kinematics Calculation:**

```python
class KinematicsAnalyzer:
    def __init__(self, fps=30, filter_cutoff=6):
        self.fps = fps
        self.dt = 1.0 / fps
        self.filter = self.create_butterworth_filter(filter_cutoff)
    
    def calculate_joint_angles(self, pose_sequence: List[Pose]) -> Dict[str, List[float]]:
        angles = {}
        
        for joint_name, joint_def in self.joint_definitions.items():
            joint_angles = []
            
            for pose in pose_sequence:
                # Get three points defining the joint
                p1 = pose.landmarks[joint_def.point1]
                p2 = pose.landmarks[joint_def.point2]  # Joint center
                p3 = pose.landmarks[joint_def.point3]
                
                # Calculate angle using vectors
                angle = self.calculate_angle_between_vectors(p1, p2, p3)
                joint_angles.append(angle)
            
            # Apply smoothing filter
            angles[joint_name] = self.filter.apply(joint_angles)
        
        return angles
    
    def calculate_velocities(self, positions: List[np.ndarray]) -> List[np.ndarray]:
        velocities = []
        for i in range(1, len(positions) - 1):
            # Central difference method
            velocity = (positions[i + 1] - positions[i - 1]) / (2 * self.dt)
            velocities.append(velocity)
        
        return self.filter.apply(velocities)
```

#### 3. Stride Analysis

```python
class StrideAnalyzer:
    def __init__(self, fps=30):
        self.fps = fps
        self.contact_threshold = 0.1  # m/s for ankle velocity
    
    def detect_foot_contacts(self, ankle_positions: List[np.ndarray]) -> List[int]:
        # Calculate ankle velocities
        velocities = self.calculate_velocities(ankle_positions)
        
        # Find zero crossings in vertical velocity
        contacts = []
        for i in range(1, len(velocities)):
            if (velocities[i-1][1] > self.contact_threshold and 
                velocities[i][1] <= self.contact_threshold):
                contacts.append(i)
        
        return contacts
    
    def analyze_stride_parameters(self, pose_sequence: List[Pose]) -> StrideMetrics:
        left_ankle = [pose.landmarks['left_ankle'] for pose in pose_sequence]
        right_ankle = [pose.landmarks['right_ankle'] for pose in pose_sequence]
        
        left_contacts = self.detect_foot_contacts(left_ankle)
        right_contacts = self.detect_foot_contacts(right_ankle)
        
        return StrideMetrics(
            stride_length=self.calculate_stride_length(left_contacts, right_contacts),
            stride_frequency=self.calculate_stride_frequency(left_contacts, right_contacts),
            contact_time=self.calculate_contact_times(left_contacts, right_contacts),
            flight_time=self.calculate_flight_times(left_contacts, right_contacts)
        )
```

#### 4. Ground Reaction Force Estimation

```python
class GRFAnalyzer:
    def __init__(self, body_mass=70.0):
        self.body_mass = body_mass
        self.g = 9.81  # Gravitational acceleration
        self.segment_params = self.load_anthropometric_data()
    
    def estimate_grf(self, pose_sequence: List[Pose], contacts: List[int]) -> List[np.ndarray]:
        forces = []
        
        for i, pose in enumerate(pose_sequence):
            if i in contacts:
                # Calculate center of mass acceleration
                com_accel = self.calculate_com_acceleration(pose_sequence, i)
                
                # Spring-mass model for force estimation
                vertical_force = self.body_mass * (self.g + com_accel[1])
                horizontal_force = self.body_mass * com_accel[0]
                
                forces.append(np.array([horizontal_force, vertical_force]))
            else:
                forces.append(np.array([0.0, 0.0]))
        
        return forces
```

## Integration in Morphine Platform

### Real-Time Processing Pipeline

```python
class MorphineVisionProcessor:
    def __init__(self):
        self.vibrio = VibrioAnalyzer(
            detection_model='yolov8s.pt',
            tracking_params={'max_age': 30, 'min_hits': 3}
        )
        self.moriarty = MoriartyPipeline(
            pose_complexity=1,
            enable_biomechanics=True
        )
        
    async def process_stream_frame(self, frame: np.ndarray, timestamp: float) -> AnalyticsResult:
        # Parallel processing
        vibrio_task = asyncio.create_task(
            self.vibrio.analyze_frame_async(frame, timestamp)
        )
        moriarty_task = asyncio.create_task(
            self.moriarty.analyze_frame_async(frame, timestamp)
        )
        
        vibrio_result, moriarty_result = await asyncio.gather(
            vibrio_task, moriarty_task
        )
        
        # Fuse results
        return self.fuse_analytics(vibrio_result, moriarty_result)
    
    def fuse_analytics(self, vibrio_result: VibrioResult, 
                      moriarty_result: MoriartyResult) -> AnalyticsResult:
        return AnalyticsResult(
            detections=vibrio_result.detections,
            tracks=vibrio_result.tracks,
            speeds=vibrio_result.speeds,
            poses=moriarty_result.poses,
            biomechanics=moriarty_result.biomechanics,
            stride_metrics=moriarty_result.stride_metrics,
            timestamp=vibrio_result.timestamp
        )
```

### Performance Optimization

| Component | Optimization Technique | Performance Gain |
|-----------|----------------------|-----------------|
| **Detection** | TensorRT optimization | 2-3x speedup |
| **Tracking** | Kalman filter pruning | 40% memory reduction |
| **Pose Estimation** | Model quantization | 1.5x speedup |
| **Analytics** | GPU batch processing | 4x throughput |
| **Memory** | Frame buffer recycling | 60% memory savings |

### Use Cases & Applications

#### Sports Broadcasting
- **Real-time athlete tracking** with speed and performance metrics
- **Automated highlight detection** based on biomechanical analysis
- **Interactive overlays** showing pose estimation and analytics

#### Gaming & Esports
- **Player movement analysis** for strategy insights
- **Performance metrics** for competitive analysis
- **Automated camera tracking** following key players

#### Fitness & Training
- **Form analysis** with pose correction suggestions
- **Performance tracking** over time
- **Injury prevention** through biomechanical monitoring

#### Research & Development
- **Motion capture** without specialized equipment
- **Biomechanical research** using standard video
- **Performance optimization** for athletes

---

## Next Steps

- [Streaming Implementation](/streaming) - Learn how CV integrates with video streaming
- [Micro-Betting System](/micro-betting) - See how analytics drive betting mechanics
- [API Reference](/api-reference) - Explore the computer vision APIs
- [Getting Started](/getting-started) - Set up the CV pipeline locally 