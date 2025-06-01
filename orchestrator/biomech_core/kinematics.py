"""
Kinematics Module
----------------
Functions for analyzing and calculating kinematic parameters of human movement
including joint angles, angular velocities, and accelerations.

These implementations are based on the KinematicsAngular2D.ipynb, KinematicsParticle.ipynb,
and KinematicsOfRigidBody.ipynb notebooks from the BMC-master repository.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import pandas as pd
from scipy import signal
from scipy.spatial.transform import Rotation as R
import os
import json

def calculate_joint_angles(
    joint_positions: Dict[str, np.ndarray], 
    segments: List[str] = None,
    angle_convention: str = 'anatomical',
    degrees: bool = True
) -> Dict[str, float]:
    """
    Calculate joint angles from joint positions.
    
    Args:
        joint_positions: Dictionary mapping joint names to 3D positions (x,y,z)
        segments: List of segment names to include (None for all)
        angle_convention: 'anatomical' or 'mechanical'
        degrees: Whether to return angles in degrees (True) or radians (False)
        
    Returns:
        Dictionary with calculated joint angles
    """
    # Default segments if none provided
    if segments is None:
        # Detect available segments from joint positions
        all_joints = list(joint_positions.keys())
        segments = []
        
        # Common segment pairs
        joint_pairs = [
            ('ankle', 'knee'), ('knee', 'hip'), ('hip', 'pelvis'),
            ('shoulder', 'elbow'), ('elbow', 'wrist'),
            ('neck', 'head'), ('pelvis', 'neck')
        ]
        
        # Check which segments are available
        for proximal, distal in joint_pairs:
            if proximal in all_joints and distal in all_joints:
                segments.append(f"{proximal}_{distal}")
    
    # Initialize results
    results = {}
    
    # Calculate angles for each segment
    for segment in segments:
        # Extract joint names
        joints = segment.split('_')
        if len(joints) != 2:
            print(f"Warning: Segment '{segment}' does not follow naming convention 'proximal_distal'. Skipping.")
            continue
            
        proximal_joint, distal_joint = joints
        
        if proximal_joint not in joint_positions or distal_joint not in joint_positions:
            print(f"Warning: Joint '{proximal_joint}' or '{distal_joint}' not found in joint positions. Skipping.")
            continue
        
        # Get joint positions
        proximal_pos = joint_positions[proximal_joint]
        distal_pos = joint_positions[distal_joint]
        
        # Calculate segment vector
        segment_vector = distal_pos - proximal_pos
        
        # Calculate angle relative to the vertical (z-axis)
        # Project onto the sagittal plane (y-z plane)
        y = segment_vector[1]
        z = segment_vector[2]
        
        # Calculate angle using arctan2
        angle = np.arctan2(y, z)
        
        # Adjust based on convention
        if angle_convention == 'anatomical':
            # Anatomical: measured from the vertical (z-axis)
            pass  # Already calculated this way
        elif angle_convention == 'mechanical':
            # Mechanical: measured from the horizontal (y-axis)
            angle = np.pi/2 - angle
        
        # Convert to degrees if requested
        if degrees:
            angle = np.degrees(angle)
        
        # Store result
        results[segment] = angle
    
    return results

def calculate_joint_angles_3d(
    joint_positions: Dict[str, np.ndarray],
    reference_frame: str = 'global',
    rotation_sequence: str = 'xyz',
    degrees: bool = True
) -> Dict[str, Dict[str, Union[float, np.ndarray]]]:
    """
    Calculate 3D joint angles using rotation matrices or Euler angles.
    
    Args:
        joint_positions: Dictionary mapping joint names to 3D positions
        reference_frame: 'global' or 'local'
        rotation_sequence: Sequence of rotations (e.g., 'xyz', 'zyx')
        degrees: Whether to return angles in degrees (True) or radians (False)
        
    Returns:
        Dictionary with joint angles and rotation matrices
    """
    # Define anatomical joint chains
    joint_chains = {
        'right_leg': ['right_hip', 'right_knee', 'right_ankle', 'right_foot'],
        'left_leg': ['left_hip', 'left_knee', 'left_ankle', 'left_foot'],
        'right_arm': ['right_shoulder', 'right_elbow', 'right_wrist', 'right_hand'],
        'left_arm': ['left_shoulder', 'left_elbow', 'left_wrist', 'left_hand'],
        'spine': ['pelvis', 'lumbar', 'thoracic', 'neck', 'head']
    }
    
    # Initialize results
    results = {
        'joint_angles': {},
        'segment_orientations': {},
        'rotation_matrices': {}
    }
    
    # Process each joint chain
    for chain_name, chain in joint_chains.items():
        chain_angles = {}
        
        # Skip chains with insufficient joint data
        if not all(joint in joint_positions for joint in chain):
            continue
        
        # Process adjacent joints in the chain
        for i in range(len(chain) - 2):
            proximal_joint = chain[i]
            middle_joint = chain[i + 1]
            distal_joint = chain[i + 2]
            
            # Get joint positions
            p1 = joint_positions[proximal_joint]
            p2 = joint_positions[middle_joint]
            p3 = joint_positions[distal_joint]
            
            # Calculate segment vectors
            v1 = p2 - p1  # Proximal segment
            v2 = p3 - p2  # Distal segment
            
            # Normalize vectors
            v1_norm = v1 / np.linalg.norm(v1)
            v2_norm = v2 / np.linalg.norm(v2)
            
            # Calculate joint angle (angle between segments)
            dot_product = np.dot(v1_norm, v2_norm)
            # Ensure dot product is within valid range for arccos
            dot_product = np.clip(dot_product, -1.0, 1.0)
            angle = np.arccos(dot_product)
            
            # Convert to degrees if requested
            if degrees:
                angle = np.degrees(angle)
            
            # Store result
            joint_name = f"{proximal_joint}_{middle_joint}_{distal_joint}"
            chain_angles[joint_name] = angle
            
            # Calculate and store rotation matrix
            if reference_frame == 'global':
                # Define reference frame (z-up for global)
                z_axis = np.array([0, 0, 1])
                
                # Calculate reference vectors for proximal segment
                y_axis_proximal = np.cross(z_axis, v1_norm)
                if np.linalg.norm(y_axis_proximal) > 1e-10:
                    y_axis_proximal = y_axis_proximal / np.linalg.norm(y_axis_proximal)
                else:
                    # Handle case when vectors are parallel
                    y_axis_proximal = np.array([0, 1, 0])
                
                x_axis_proximal = np.cross(y_axis_proximal, z_axis)
                
                # Form rotation matrix for proximal segment
                rotation_proximal = np.column_stack((x_axis_proximal, y_axis_proximal, z_axis))
                
                # Calculate reference vectors for distal segment
                y_axis_distal = np.cross(z_axis, v2_norm)
                if np.linalg.norm(y_axis_distal) > 1e-10:
                    y_axis_distal = y_axis_distal / np.linalg.norm(y_axis_distal)
                else:
                    y_axis_distal = np.array([0, 1, 0])
                
                x_axis_distal = np.cross(y_axis_distal, z_axis)
                
                # Form rotation matrix for distal segment
                rotation_distal = np.column_stack((x_axis_distal, y_axis_distal, z_axis))
                
                # Calculate relative rotation between segments
                relative_rotation = np.dot(rotation_distal, rotation_proximal.T)
                
                # Store rotation matrices
                results['rotation_matrices'][f"{proximal_joint}_{middle_joint}"] = rotation_proximal
                results['rotation_matrices'][f"{middle_joint}_{distal_joint}"] = rotation_distal
                results['rotation_matrices'][joint_name] = relative_rotation
                
                # Extract Euler angles based on rotation sequence
                try:
                    rot = R.from_matrix(relative_rotation)
                    euler_angles = rot.as_euler(rotation_sequence, degrees=degrees)
                    
                    # Store Euler angles
                    for j, axis in enumerate(rotation_sequence):
                        chain_angles[f"{joint_name}_{axis}"] = euler_angles[j]
                except Exception as e:
                    print(f"Error calculating Euler angles for {joint_name}: {str(e)}")
        
        # Store results for this chain
        results['joint_angles'][chain_name] = chain_angles
    
    return results

def calculate_angular_velocity(
    joint_angles: Dict[str, List[float]],
    time_data: List[float],
    smooth: bool = True,
    filter_cutoff: float = 6.0,
    sampling_rate: float = 100.0
) -> Dict[str, List[float]]:
    """
    Calculate angular velocities from joint angle time series.
    
    Args:
        joint_angles: Dictionary mapping joint names to lists of angle values over time
        time_data: List of time points corresponding to joint angles
        smooth: Whether to apply smoothing to the calculated velocities
        filter_cutoff: Cutoff frequency for the smoothing filter in Hz
        sampling_rate: Sampling rate of the data in Hz
        
    Returns:
        Dictionary with calculated angular velocities
    """
    # Initialize results
    angular_velocities = {}
    
    # Convert time data to numpy array if it's not already
    time_array = np.array(time_data)
    
    # Process each joint
    for joint_name, angles in joint_angles.items():
        # Convert angles to numpy array
        angle_array = np.array(angles)
        
        # Calculate time differences
        time_diff = np.diff(time_array)
        
        # Avoid division by zero
        time_diff[time_diff == 0] = np.finfo(float).eps
        
        # Calculate angular velocity using central difference method
        velocity = np.zeros_like(angle_array)
        velocity[1:-1] = (angle_array[2:] - angle_array[:-2]) / (time_array[2:] - time_array[:-2])
        velocity[0] = (angle_array[1] - angle_array[0]) / time_diff[0]
        velocity[-1] = (angle_array[-1] - angle_array[-2]) / time_diff[-1]
        
        # Apply smoothing if requested
        if smooth:
            # Design Butterworth filter
            nyquist = 0.5 * sampling_rate
            normal_cutoff = filter_cutoff / nyquist
            b, a = signal.butter(2, normal_cutoff, 'low')
            
            # Apply filter
            velocity = signal.filtfilt(b, a, velocity)
        
        # Store result
        angular_velocities[joint_name] = velocity.tolist()
    
    return angular_velocities

def calculate_angular_acceleration(
    angular_velocities: Dict[str, List[float]],
    time_data: List[float],
    smooth: bool = True,
    filter_cutoff: float = 6.0,
    sampling_rate: float = 100.0
) -> Dict[str, List[float]]:
    """
    Calculate angular accelerations from angular velocity time series.
    
    Args:
        angular_velocities: Dictionary mapping joint names to lists of angular velocity values
        time_data: List of time points corresponding to angular velocities
        smooth: Whether to apply smoothing to the calculated accelerations
        filter_cutoff: Cutoff frequency for the smoothing filter in Hz
        sampling_rate: Sampling rate of the data in Hz
        
    Returns:
        Dictionary with calculated angular accelerations
    """
    # Initialize results
    angular_accelerations = {}
    
    # Convert time data to numpy array if it's not already
    time_array = np.array(time_data)
    
    # Process each joint
    for joint_name, velocities in angular_velocities.items():
        # Convert velocities to numpy array
        velocity_array = np.array(velocities)
        
        # Calculate time differences
        time_diff = np.diff(time_array)
        
        # Avoid division by zero
        time_diff[time_diff == 0] = np.finfo(float).eps
        
        # Calculate angular acceleration using central difference method
        acceleration = np.zeros_like(velocity_array)
        acceleration[1:-1] = (velocity_array[2:] - velocity_array[:-2]) / (time_array[2:] - time_array[:-2])
        acceleration[0] = (velocity_array[1] - velocity_array[0]) / time_diff[0]
        acceleration[-1] = (velocity_array[-1] - velocity_array[-2]) / time_diff[-1]
        
        # Apply smoothing if requested
        if smooth:
            # Design Butterworth filter
            nyquist = 0.5 * sampling_rate
            normal_cutoff = filter_cutoff / nyquist
            b, a = signal.butter(2, normal_cutoff, 'low')
            
            # Apply filter
            acceleration = signal.filtfilt(b, a, acceleration)
        
        # Store result
        angular_accelerations[joint_name] = acceleration.tolist()
    
    return angular_accelerations

def calculate_linear_velocity(
    positions: Dict[str, List[np.ndarray]],
    time_data: List[float],
    smooth: bool = True,
    filter_cutoff: float = 6.0,
    sampling_rate: float = 100.0
) -> Dict[str, List[np.ndarray]]:
    """
    Calculate linear velocities from position time series.
    
    Args:
        positions: Dictionary mapping point names to lists of position vectors over time
        time_data: List of time points corresponding to positions
        smooth: Whether to apply smoothing to the calculated velocities
        filter_cutoff: Cutoff frequency for the smoothing filter in Hz
        sampling_rate: Sampling rate of the data in Hz
        
    Returns:
        Dictionary with calculated linear velocities
    """
    # Initialize results
    linear_velocities = {}
    
    # Convert time data to numpy array if it's not already
    time_array = np.array(time_data)
    
    # Process each point
    for point_name, pos_data in positions.items():
        # Convert position data to numpy array
        pos_array = np.array(pos_data)
        
        # Initialize velocity array
        vel_array = np.zeros_like(pos_array)
        
        # Calculate time differences
        time_diff = np.diff(time_array)
        
        # Avoid division by zero
        time_diff[time_diff == 0] = np.finfo(float).eps
        
        # Calculate velocity using central difference method
        for i in range(1, len(pos_array) - 1):
            vel_array[i] = (pos_array[i+1] - pos_array[i-1]) / (time_array[i+1] - time_array[i-1])
        
        # Handle boundaries
        vel_array[0] = (pos_array[1] - pos_array[0]) / (time_array[1] - time_array[0])
        vel_array[-1] = (pos_array[-1] - pos_array[-2]) / (time_array[-1] - time_array[-2])
        
        # Apply smoothing if requested
        if smooth:
            # Design Butterworth filter
            nyquist = 0.5 * sampling_rate
            normal_cutoff = filter_cutoff / nyquist
            b, a = signal.butter(2, normal_cutoff, 'low')
            
            # Apply filter to each dimension separately
            for dim in range(vel_array.shape[1]):
                vel_array[:, dim] = signal.filtfilt(b, a, vel_array[:, dim])
        
        # Store result
        linear_velocities[point_name] = vel_array.tolist()
    
    return linear_velocities

def calculate_acceleration(
    velocities: Dict[str, List[np.ndarray]],
    time_data: List[float],
    smooth: bool = True,
    filter_cutoff: float = 6.0,
    sampling_rate: float = 100.0
) -> Dict[str, List[np.ndarray]]:
    """
    Calculate accelerations from velocity time series.
    
    Args:
        velocities: Dictionary mapping point names to lists of velocity vectors
        time_data: List of time points corresponding to velocities
        smooth: Whether to apply smoothing to the calculated accelerations
        filter_cutoff: Cutoff frequency for the smoothing filter in Hz
        sampling_rate: Sampling rate of the data in Hz
        
    Returns:
        Dictionary with calculated accelerations
    """
    # Initialize results
    accelerations = {}
    
    # Convert time data to numpy array if it's not already
    time_array = np.array(time_data)
    
    # Process each point
    for point_name, vel_data in velocities.items():
        # Convert velocity data to numpy array
        vel_array = np.array(vel_data)
        
        # Initialize acceleration array
        acc_array = np.zeros_like(vel_array)
        
        # Calculate time differences
        time_diff = np.diff(time_array)
        
        # Avoid division by zero
        time_diff[time_diff == 0] = np.finfo(float).eps
        
        # Calculate acceleration using central difference method
        for i in range(1, len(vel_array) - 1):
            acc_array[i] = (vel_array[i+1] - vel_array[i-1]) / (time_array[i+1] - time_array[i-1])
        
        # Handle boundaries
        acc_array[0] = (vel_array[1] - vel_array[0]) / (time_array[1] - time_array[0])
        acc_array[-1] = (vel_array[-1] - vel_array[-2]) / (time_array[-1] - time_array[-2])
        
        # Apply smoothing if requested
        if smooth:
            # Design Butterworth filter
            nyquist = 0.5 * sampling_rate
            normal_cutoff = filter_cutoff / nyquist
            b, a = signal.butter(2, normal_cutoff, 'low')
            
            # Apply filter to each dimension separately
            for dim in range(acc_array.shape[1]):
                acc_array[:, dim] = signal.filtfilt(b, a, acc_array[:, dim])
        
        # Store result
        accelerations[point_name] = acc_array.tolist()
    
    return accelerations

def calculate_orientation_from_markers(
    markers: Dict[str, np.ndarray],
    segment_definitions: Dict[str, List[str]]
) -> Dict[str, Dict[str, Union[np.ndarray, R]]]:
    """
    Calculate segment orientations from marker positions.
    
    Args:
        markers: Dictionary mapping marker names to 3D positions
        segment_definitions: Dictionary defining which markers to use for each segment
        
    Returns:
        Dictionary with calculated segment orientations
    """
    # Initialize results
    orientations = {}
    
    # Process each segment
    for segment_name, marker_names in segment_definitions.items():
        # Check if we have enough markers for this segment
        if len(marker_names) < 3:
            print(f"Warning: Segment '{segment_name}' requires at least 3 markers. Skipping.")
            continue
            
        # Check if all required markers are available
        if not all(marker in markers for marker in marker_names):
            print(f"Warning: Not all markers available for segment '{segment_name}'. Skipping.")
            continue
        
        # Get marker positions
        marker_positions = [markers[marker] for marker in marker_names]
        
        # Calculate segment coordinate system
        # Origin is the first marker
        origin = marker_positions[0]
        
        # Primary axis (z-axis) from first to second marker
        z_axis = marker_positions[1] - origin
        z_axis = z_axis / np.linalg.norm(z_axis)
        
        # Temporary vector from first to third marker
        temp_vec = marker_positions[2] - origin
        
        # Calculate y-axis (perpendicular to z-axis and temp_vec)
        y_axis = np.cross(z_axis, temp_vec)
        y_axis = y_axis / np.linalg.norm(y_axis)
        
        # Calculate x-axis (perpendicular to y-axis and z-axis)
        x_axis = np.cross(y_axis, z_axis)
        
        # Form rotation matrix
        rotation_matrix = np.column_stack((x_axis, y_axis, z_axis))
        
        # Store results
        orientations[segment_name] = {
            'origin': origin,
            'x_axis': x_axis,
            'y_axis': y_axis,
            'z_axis': z_axis,
            'rotation_matrix': rotation_matrix,
            'rotation': R.from_matrix(rotation_matrix)
        }
    
    return orientations

def project_angle_to_plane(
    joint_positions: Dict[str, np.ndarray],
    plane: str = 'sagittal',
    segment_pair: Tuple[str, str, str] = None,
    degrees: bool = True
) -> float:
    """
    Calculate angle projected onto a specified plane.
    
    Args:
        joint_positions: Dictionary mapping joint names to 3D positions
        plane: Plane to project onto ('sagittal', 'frontal', or 'transverse')
        segment_pair: Tuple of (proximal_joint, middle_joint, distal_joint)
        degrees: Whether to return angles in degrees (True) or radians (False)
        
    Returns:
        Projected angle
    """
    if segment_pair is None or len(segment_pair) != 3:
        raise ValueError("segment_pair must be a tuple of three joint names")
    
    proximal_joint, middle_joint, distal_joint = segment_pair
    
    # Check if all joints are in the data
    if not all(joint in joint_positions for joint in segment_pair):
        missing = [joint for joint in segment_pair if joint not in joint_positions]
        raise ValueError(f"Missing joint positions for: {', '.join(missing)}")
    
    # Get joint positions
    p1 = joint_positions[proximal_joint]
    p2 = joint_positions[middle_joint]
    p3 = joint_positions[distal_joint]
    
    # Calculate segment vectors
    v1 = p2 - p1  # Proximal segment
    v2 = p3 - p2  # Distal segment
    
    # Project vectors onto the specified plane
    if plane == 'sagittal':
        # y-z plane (x = 0)
        v1_proj = np.array([0, v1[1], v1[2]])
        v2_proj = np.array([0, v2[1], v2[2]])
    elif plane == 'frontal':
        # x-z plane (y = 0)
        v1_proj = np.array([v1[0], 0, v1[2]])
        v2_proj = np.array([v2[0], 0, v2[2]])
    elif plane == 'transverse':
        # x-y plane (z = 0)
        v1_proj = np.array([v1[0], v1[1], 0])
        v2_proj = np.array([v2[0], v2[1], 0])
    else:
        raise ValueError(f"Unknown plane: {plane}")
    
    # Normalize projected vectors
    v1_norm = np.linalg.norm(v1_proj)
    v2_norm = np.linalg.norm(v2_proj)
    
    # Avoid division by zero
    if v1_norm < 1e-10 or v2_norm < 1e-10:
        return 0.0
    
    v1_proj = v1_proj / v1_norm
    v2_proj = v2_proj / v2_norm
    
    # Calculate angle between projected vectors
    dot_product = np.dot(v1_proj, v2_proj)
    dot_product = np.clip(dot_product, -1.0, 1.0)  # Ensure dot product is within valid range
    angle = np.arccos(dot_product)
    
    # Convert to degrees if requested
    if degrees:
        angle = np.degrees(angle)
    
    return angle

def calculate_angular_kinematics_from_trajectory(
    trajectory: Dict[str, List[np.ndarray]],
    time_data: List[float],
    segment_definitions: Dict[str, List[str]],
    joint_definitions: Dict[str, Tuple[str, str, str]],
    smooth: bool = True,
    filter_cutoff: float = 6.0,
    sampling_rate: float = 100.0
) -> Dict[str, Any]:
    """
    Calculate comprehensive angular kinematics from marker trajectory data.
    
    Args:
        trajectory: Dictionary mapping marker names to lists of 3D positions over time
        time_data: List of time points corresponding to trajectory data
        segment_definitions: Dictionary defining which markers to use for each segment
        joint_definitions: Dictionary defining joints as (proximal segment, distal segment, rotation axis)
        smooth: Whether to apply smoothing to calculated derivatives
        filter_cutoff: Cutoff frequency for the smoothing filter in Hz
        sampling_rate: Sampling rate of the data in Hz
        
    Returns:
        Dictionary with calculated angular kinematics
    """
    # Initialize results structure
    results = {
        'segment_orientations': [],
        'joint_angles': {},
        'joint_angular_velocities': {},
        'joint_angular_accelerations': {}
    }
    
    # Initialize temporary arrays for time series data
    num_frames = len(time_data)
    joint_angle_series = {joint_name: np.zeros(num_frames) for joint_name in joint_definitions}
    
    # Process each frame
    for frame in range(num_frames):
        # Extract marker positions for this frame
        frame_markers = {
            marker_name: trajectory[marker_name][frame] 
            for marker_name in trajectory
        }
        
        # Calculate segment orientations for this frame
        orientations = calculate_orientation_from_markers(frame_markers, segment_definitions)
        results['segment_orientations'].append(orientations)
        
        # Calculate joint angles for this frame
        for joint_name, (proximal_seg, distal_seg, axis) in joint_definitions.items():
            if proximal_seg in orientations and distal_seg in orientations:
                # Get rotation matrices
                R_proximal = orientations[proximal_seg]['rotation_matrix']
                R_distal = orientations[distal_seg]['rotation_matrix']
                
                # Calculate relative rotation
                R_relative = np.dot(R_distal, R_proximal.T)
                
                # Convert to rotation object
                rot = R.from_matrix(R_relative)
                
                # Extract Euler angles
                euler = rot.as_euler('xyz', degrees=True)
                
                # Store angle for this frame based on specified axis
                if axis == 'x':
                    joint_angle_series[joint_name][frame] = euler[0]
                elif axis == 'y':
                    joint_angle_series[joint_name][frame] = euler[1]
                elif axis == 'z':
                    joint_angle_series[joint_name][frame] = euler[2]
                else:
                    print(f"Warning: Unknown rotation axis '{axis}' for joint '{joint_name}'. Using x-axis.")
                    joint_angle_series[joint_name][frame] = euler[0]
    
    # Store joint angles in results
    for joint_name, angles in joint_angle_series.items():
        results['joint_angles'][joint_name] = angles.tolist()
    
    # Calculate angular velocities
    results['joint_angular_velocities'] = calculate_angular_velocity(
        results['joint_angles'], time_data, smooth, filter_cutoff, sampling_rate
    )
    
    # Calculate angular accelerations
    results['joint_angular_accelerations'] = calculate_angular_acceleration(
        results['joint_angular_velocities'], time_data, smooth, filter_cutoff, sampling_rate
    )
    
    return results

def detect_events_from_kinematics(
    joint_angles: Dict[str, List[float]],
    joint_velocities: Dict[str, List[float]],
    time_data: List[float],
    event_definitions: Dict[str, Dict[str, Any]]
) -> Dict[str, List[Dict[str, float]]]:
    """
    Detect biomechanical events from kinematic data.
    
    Args:
        joint_angles: Dictionary mapping joint names to angle time series
        joint_velocities: Dictionary mapping joint names to velocity time series
        time_data: List of time points
        event_definitions: Dictionary defining events to detect
        
    Returns:
        Dictionary with detected events
    """
    # Initialize results
    events = {}
    
    # Process each event type
    for event_name, definition in event_definitions.items():
        # Initialize list for this event type
        events[event_name] = []
        
        # Extract definition parameters
        joint = definition.get('joint')
        condition = definition.get('condition', 'threshold')
        threshold = definition.get('threshold', 0)
        direction = definition.get('direction', 'increasing')
        use_velocity = definition.get('use_velocity', False)
        
        # Check if the required joint data is available
        if joint not in joint_angles:
            print(f"Warning: Joint '{joint}' not found in kinematic data. Skipping event '{event_name}'.")
            continue
        
        # Get the relevant data series
        if use_velocity:
            if joint not in joint_velocities:
                print(f"Warning: Velocity data for joint '{joint}' not available. Skipping event '{event_name}'.")
                continue
            data_series = joint_velocities[joint]
        else:
            data_series = joint_angles[joint]
        
        # Detect events based on condition
        if condition == 'threshold':
            # Find where the data crosses the threshold in the specified direction
            for i in range(1, len(data_series)):
                if (direction == 'increasing' and 
                    data_series[i-1] < threshold and data_series[i] >= threshold) or \
                   (direction == 'decreasing' and 
                    data_series[i-1] > threshold and data_series[i] <= threshold):
                    
                    # Calculate precise crossing time via linear interpolation
                    t0 = time_data[i-1]
                    t1 = time_data[i]
                    v0 = data_series[i-1]
                    v1 = data_series[i]
                    
                    # Avoid division by zero
                    if v1 == v0:
                        crossing_time = t0
                    else:
                        ratio = (threshold - v0) / (v1 - v0)
                        crossing_time = t0 + ratio * (t1 - t0)
                    
                    # Store the event
                    events[event_name].append({
                        'time': crossing_time,
                        'frame_index': i,
                        'value': threshold
                    })
                    
        elif condition == 'max':
            # Find local maxima
            for i in range(1, len(data_series) - 1):
                if data_series[i] > data_series[i-1] and data_series[i] > data_series[i+1]:
                    # Store the event
                    events[event_name].append({
                        'time': time_data[i],
                        'frame_index': i,
                        'value': data_series[i]
                    })
                    
        elif condition == 'min':
            # Find local minima
            for i in range(1, len(data_series) - 1):
                if data_series[i] < data_series[i-1] and data_series[i] < data_series[i+1]:
                    # Store the event
                    events[event_name].append({
                        'time': time_data[i],
                        'frame_index': i,
                        'value': data_series[i]
                    })
    
    return events

def interpolate_missing_markers(
    trajectory: Dict[str, List[np.ndarray]],
    max_gap_frames: int = 10
) -> Dict[str, List[np.ndarray]]:
    """
    Interpolate missing markers in trajectory data.
    
    Args:
        trajectory: Dictionary mapping marker names to lists of 3D positions
        max_gap_frames: Maximum gap size to interpolate
        
    Returns:
        Trajectory with interpolated gaps
    """
    # Create a copy of the input trajectory
    result = {marker: positions.copy() for marker, positions in trajectory.items()}
    
    # Process each marker
    for marker, positions in result.items():
        # Convert to numpy array if it's not already
        if not isinstance(positions, np.ndarray):
            positions = np.array(positions)
        
        # Find missing frames (where position is None or NaN)
        missing_frames = []
        current_gap = []
        
        for i in range(len(positions)):
            # Check if this frame is missing
            is_missing = False
            
            if positions[i] is None:
                is_missing = True
            elif isinstance(positions[i], np.ndarray) and np.isnan(positions[i]).any():
                is_missing = True
            
            if is_missing:
                # Add to current gap
                current_gap.append(i)
            else:
                # If we were tracking a gap and now found a valid frame, 
                # add the gap to our list if it's not too large
                if current_gap and len(current_gap) <= max_gap_frames:
                    missing_frames.append(current_gap)
                
                # Reset current gap
                current_gap = []
        
        # Handle any remaining gap at the end
        if current_gap and len(current_gap) <= max_gap_frames:
            missing_frames.append(current_gap)
        
        # Interpolate each gap
        for gap in missing_frames:
            # Get frames before and after the gap
            before_frame = gap[0] - 1
            after_frame = gap[-1] + 1
            
            # Skip if gap is at the beginning or end of the data
            if before_frame < 0 or after_frame >= len(positions):
                continue
            
            # Get positions before and after the gap
            before_pos = positions[before_frame]
            after_pos = positions[after_frame]
            
            # Calculate interval for interpolation
            total_frames = after_frame - before_frame + 1
            
            # Interpolate each frame in the gap
            for i, frame in enumerate(gap):
                # Calculate interpolation ratio
                ratio = (i + 1) / total_frames
                
                # Linear interpolation
                positions[frame] = before_pos + ratio * (after_pos - before_pos)
        
        # Update the result
        result[marker] = positions
    
    return result 