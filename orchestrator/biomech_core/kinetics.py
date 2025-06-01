"""
Kinetics Module
-------------
Functions for calculating kinetic parameters including forces, moments,
energy, and power for biomechanical analysis.

These implementations are based on the KineticsFundamentalConcepts.ipynb,
FreeBodyDiagramForRigidBodies.ipynb, and Kinetics3dRigidBody.ipynb notebooks 
from the BMC-master repository.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import os
import json

# Constants
GRAVITY = 9.81  # m/s^2

def calculate_joint_forces(
    joint_positions: Dict[str, np.ndarray],
    segment_params: Dict[str, Dict[str, float]],
    joint_accelerations: Dict[str, np.ndarray],
    external_forces: Optional[Dict[str, np.ndarray]] = None,
    ground_reaction_force: Optional[np.ndarray] = None,
    ground_reaction_point: Optional[np.ndarray] = None
) -> Dict[str, np.ndarray]:
    """
    Calculate joint forces using inverse dynamics.
    
    Args:
        joint_positions: Dictionary mapping joint names to 3D positions
        segment_params: Dictionary with segment parameters (mass, COM position, etc.)
        joint_accelerations: Dictionary mapping joint names to 3D accelerations
        external_forces: Optional dictionary of external forces
        ground_reaction_force: Optional ground reaction force vector
        ground_reaction_point: Optional application point of ground reaction force
        
    Returns:
        Dictionary with calculated joint forces
    """
    # Initialize results
    joint_forces = {}
    
    # Define joint chains (distal to proximal)
    joint_chains = {
        'right_leg': ['right_foot', 'right_ankle', 'right_knee', 'right_hip'],
        'left_leg': ['left_foot', 'left_ankle', 'left_knee', 'left_hip'],
        'right_arm': ['right_hand', 'right_wrist', 'right_elbow', 'right_shoulder'],
        'left_arm': ['left_hand', 'left_wrist', 'left_elbow', 'left_shoulder'],
        'spine': ['head', 'neck', 'thoracic', 'lumbar', 'pelvis']
    }
    
    # Process each joint chain
    for chain_name, chain in joint_chains.items():
        # Skip chains with insufficient joint data
        if not all(joint in joint_positions for joint in chain):
            continue
        
        # Iteratively calculate joint forces from distal to proximal
        for i in range(len(chain) - 1):
            distal_joint = chain[i]
            proximal_joint = chain[i + 1]
            segment_name = f"{distal_joint}_{proximal_joint}"
            
            # Skip if segment data is not available
            if segment_name not in segment_params['segments']:
                continue
            
            # Get segment data
            segment_data = segment_params['segments'][segment_name]
            segment_mass = segment_data['segment_mass_kg']
            
            # Get joint positions
            p_distal = joint_positions[distal_joint]
            p_proximal = joint_positions[proximal_joint]
            
            # Calculate segment COM position
            # Assuming COM position is given as ratio along segment from proximal to distal
            com_ratio = segment_data.get('COM', 0.5)  # Default to middle if not specified
            p_com = p_proximal + com_ratio * (p_distal - p_proximal)
            
            # Calculate gravitational force
            f_gravity = np.array([0, 0, -segment_mass * GRAVITY])
            
            # Calculate inertial force (mass * acceleration)
            # Use joint accelerations or default to zero
            a_com = np.zeros(3)
            if distal_joint in joint_accelerations:
                a_distal = joint_accelerations[distal_joint]
                if proximal_joint in joint_accelerations:
                    a_proximal = joint_accelerations[proximal_joint]
                    # Interpolate to estimate COM acceleration
                    a_com = a_proximal + com_ratio * (a_distal - a_proximal)
                else:
                    a_com = a_distal
            
            f_inertia = segment_mass * a_com
            
            # Add external forces if applicable
            f_external = np.zeros(3)
            if external_forces and segment_name in external_forces:
                f_external = external_forces[segment_name]
            
            # Add ground reaction force if this is a foot segment and GRF is provided
            f_grf = np.zeros(3)
            if ground_reaction_force is not None and distal_joint.endswith('foot'):
                # Check if this is the segment in contact with the ground
                if ground_reaction_point is not None:
                    # Simple check if ground reaction point is close to this segment
                    # In a real application, more sophisticated contact detection would be used
                    distance_to_segment = np.linalg.norm(np.cross(
                        p_distal - p_proximal,
                        p_proximal - ground_reaction_point
                    )) / np.linalg.norm(p_distal - p_proximal)
                    
                    if distance_to_segment < 0.1:  # Arbitrary threshold
                        f_grf = ground_reaction_force
                else:
                    # If application point not specified, apply to the foot
                    f_grf = ground_reaction_force
            
            # Calculate force at distal joint (if not the endpoint)
            f_distal = np.zeros(3)
            if i > 0:
                distal_segment = f"{chain[i-1]}_{distal_joint}"
                if distal_segment in joint_forces:
                    f_distal = -joint_forces[distal_segment]  # Equal and opposite
            
            # Calculate force at proximal joint using Newton's laws
            f_proximal = f_distal + f_gravity + f_inertia - f_external - f_grf
            
            # Store result
            joint_forces[segment_name] = f_proximal
    
    return joint_forces

def calculate_joint_moments(
    joint_positions: Dict[str, np.ndarray],
    joint_forces: Dict[str, np.ndarray],
    segment_params: Dict[str, Dict[str, float]],
    joint_angular_accelerations: Dict[str, np.ndarray],
    external_moments: Optional[Dict[str, np.ndarray]] = None
) -> Dict[str, np.ndarray]:
    """
    Calculate joint moments using inverse dynamics.
    
    Args:
        joint_positions: Dictionary mapping joint names to 3D positions
        joint_forces: Dictionary with joint forces from calculate_joint_forces()
        segment_params: Dictionary with segment parameters
        joint_angular_accelerations: Dictionary mapping joints to angular accelerations
        external_moments: Optional dictionary of external moments
        
    Returns:
        Dictionary with calculated joint moments
    """
    # Initialize results
    joint_moments = {}
    
    # Define joint chains (distal to proximal)
    joint_chains = {
        'right_leg': ['right_foot', 'right_ankle', 'right_knee', 'right_hip'],
        'left_leg': ['left_foot', 'left_ankle', 'left_knee', 'left_hip'],
        'right_arm': ['right_hand', 'right_wrist', 'right_elbow', 'right_shoulder'],
        'left_arm': ['left_hand', 'left_wrist', 'left_elbow', 'left_shoulder'],
        'spine': ['head', 'neck', 'thoracic', 'lumbar', 'pelvis']
    }
    
    # Process each joint chain
    for chain_name, chain in joint_chains.items():
        # Skip chains with insufficient joint data
        if not all(joint in joint_positions for joint in chain):
            continue
        
        # Iteratively calculate joint moments from distal to proximal
        for i in range(len(chain) - 1):
            distal_joint = chain[i]
            proximal_joint = chain[i + 1]
            segment_name = f"{distal_joint}_{proximal_joint}"
            
            # Skip if segment data or forces are not available
            if (segment_name not in segment_params['segments'] or 
                segment_name not in joint_forces):
                continue
            
            # Get segment data
            segment_data = segment_params['segments'][segment_name]
            segment_mass = segment_data['segment_mass_kg']
            
            # Get moment of inertia (if available)
            I = segment_data.get('moment_of_inertia_about_cm_kgm2', segment_mass * 0.1**2)  # Default estimate
            
            # Get joint positions
            p_distal = joint_positions[distal_joint]
            p_proximal = joint_positions[proximal_joint]
            
            # Calculate segment COM position
            com_ratio = segment_data.get('COM', 0.5)  # Default to middle if not specified
            p_com = p_proximal + com_ratio * (p_distal - p_proximal)
            
            # Get forces
            f_proximal = joint_forces[segment_name]
            
            # Get force at distal joint (if not the endpoint)
            f_distal = np.zeros(3)
            if i > 0:
                distal_segment = f"{chain[i-1]}_{distal_joint}"
                if distal_segment in joint_forces:
                    f_distal = -joint_forces[distal_segment]  # Equal and opposite
            
            # Calculate moment due to proximal force
            m_proximal_force = np.cross(p_proximal - p_com, f_proximal)
            
            # Calculate moment due to distal force
            m_distal_force = np.cross(p_distal - p_com, f_distal)
            
            # Get angular acceleration for inertial moment
            angular_acc = np.zeros(3)
            joint_name = f"{proximal_joint}_{distal_joint}"
            if joint_name in joint_angular_accelerations:
                angular_acc = joint_angular_accelerations[joint_name]
            
            # Calculate inertial moment (I * alpha)
            m_inertia = I * angular_acc
            
            # Add external moments if applicable
            m_external = np.zeros(3)
            if external_moments and segment_name in external_moments:
                m_external = external_moments[segment_name]
            
            # Calculate moment at distal joint (if not the endpoint)
            m_distal = np.zeros(3)
            if i > 0:
                distal_segment = f"{chain[i-1]}_{distal_joint}"
                if distal_segment in joint_moments:
                    m_distal = -joint_moments[distal_segment]  # Equal and opposite
            
            # Calculate moment at proximal joint using Newton-Euler equations
            m_proximal = m_distal + m_proximal_force + m_distal_force + m_inertia - m_external
            
            # Store result
            joint_moments[segment_name] = m_proximal
    
    return joint_moments

def calculate_power(
    joint_moments: Dict[str, np.ndarray],
    joint_angular_velocities: Dict[str, np.ndarray]
) -> Dict[str, float]:
    """
    Calculate joint powers (moment * angular velocity).
    
    Args:
        joint_moments: Dictionary with joint moments
        joint_angular_velocities: Dictionary with joint angular velocities
        
    Returns:
        Dictionary with calculated joint powers
    """
    # Initialize results
    joint_powers = {}
    
    # Calculate power for each joint where we have both moment and angular velocity
    for joint_name in joint_moments:
        if joint_name in joint_angular_velocities:
            # Calculate dot product of moment and angular velocity
            power = np.dot(joint_moments[joint_name], joint_angular_velocities[joint_name])
            joint_powers[joint_name] = power
    
    return joint_powers

def calculate_work(
    joint_powers: Dict[str, List[float]],
    time_data: List[float]
) -> Dict[str, float]:
    """
    Calculate mechanical work as the integral of power over time.
    
    Args:
        joint_powers: Dictionary mapping joint names to lists of power values over time
        time_data: List of time points corresponding to power values
        
    Returns:
        Dictionary with calculated work for each joint
    """
    # Initialize results
    joint_work = {}
    
    # Calculate work for each joint
    for joint_name, powers in joint_powers.items():
        # Convert to numpy array if not already
        power_array = np.array(powers)
        time_array = np.array(time_data)
        
        # Calculate time differences
        time_diff = np.diff(time_array)
        
        # Calculate work as the integral of power over time (trapezoidal rule)
        work = 0.0
        for i in range(len(power_array) - 1):
            # Average power over the interval * time interval
            work += 0.5 * (power_array[i] + power_array[i+1]) * time_diff[i]
        
        joint_work[joint_name] = work
    
    return joint_work

def calculate_energy(
    joint_positions: Dict[str, List[np.ndarray]],
    joint_velocities: Dict[str, List[np.ndarray]],
    segment_params: Dict[str, Dict[str, float]],
    time_data: List[float]
) -> Dict[str, Dict[str, List[float]]]:
    """
    Calculate kinetic and potential energy for each segment over time.
    
    Args:
        joint_positions: Dictionary mapping joint names to lists of positions over time
        joint_velocities: Dictionary mapping joint names to lists of velocities over time
        segment_params: Dictionary with segment parameters
        time_data: List of time points
        
    Returns:
        Dictionary with kinetic and potential energy for each segment
    """
    # Initialize results
    energy = {
        'segments': {},
        'total': {
            'kinetic': [],
            'potential': [],
            'total': []
        }
    }
    
    num_frames = len(time_data)
    
    # Define segments based on available joint data
    segments = []
    all_joints = list(joint_positions.keys())
    
    # Common segment pairs
    joint_pairs = [
        ('ankle', 'knee'), ('knee', 'hip'), 
        ('shoulder', 'elbow'), ('elbow', 'wrist'),
        ('hip', 'pelvis'), ('neck', 'head'), ('pelvis', 'neck')
    ]
    
    # Check which segments we can define
    for proximal, distal in joint_pairs:
        # Check basic joints
        if proximal in all_joints and distal in all_joints:
            segments.append(f"{proximal}_{distal}")
        
        # Check for left/right prefixed joints
        if f"left_{proximal}" in all_joints and f"left_{distal}" in all_joints:
            segments.append(f"left_{proximal}_left_{distal}")
        if f"right_{proximal}" in all_joints and f"right_{distal}" in all_joints:
            segments.append(f"right_{proximal}_right_{distal}")
    
    # Initialize segment energy arrays
    for segment in segments:
        energy['segments'][segment] = {
            'kinetic': np.zeros(num_frames),
            'potential': np.zeros(num_frames),
            'total': np.zeros(num_frames)
        }
    
    # Calculate energy for each frame
    for frame in range(num_frames):
        total_kinetic = 0.0
        total_potential = 0.0
        
        # Process each segment
        for segment in segments:
            # Extract joint names
            joints = segment.split('_')
            if len(joints) == 2:
                proximal, distal = joints
            elif len(joints) == 4:
                # Handle left/right prefixes
                proximal, distal = joints[1], joints[3]
            else:
                continue
            
            # Skip if we don't have position or velocity data
            if proximal not in joint_positions[frame] or distal not in joint_positions[frame]:
                continue
            if proximal not in joint_velocities[frame] or distal not in joint_velocities[frame]:
                continue
            
            # Skip if segment data is not available
            segment_name = f"{proximal}_{distal}"
            if segment_name not in segment_params['segments']:
                continue
            
            # Get segment data
            segment_data = segment_params['segments'][segment_name]
            segment_mass = segment_data['segment_mass_kg']
            
            # Get joint positions and velocities
            p_proximal = joint_positions[frame][proximal]
            p_distal = joint_positions[frame][distal]
            v_proximal = joint_velocities[frame][proximal]
            v_distal = joint_velocities[frame][distal]
            
            # Calculate COM position and velocity
            com_ratio = segment_data.get('COM', 0.5)  # Default to middle if not specified
            p_com = p_proximal + com_ratio * (p_distal - p_proximal)
            v_com = v_proximal + com_ratio * (v_distal - v_proximal)
            
            # Get moment of inertia about COM
            I = segment_data.get('moment_of_inertia_about_cm_kgm2', segment_mass * 0.1**2)  # Default estimate
            
            # Calculate linear kinetic energy: 0.5 * m * v^2
            KE_linear = 0.5 * segment_mass * np.linalg.norm(v_com)**2
            
            # Calculate angular velocity (simplified)
            segment_vector = p_distal - p_proximal
            segment_length = np.linalg.norm(segment_vector)
            if segment_length > 0:
                segment_axis = segment_vector / segment_length
                v_relative = v_distal - v_proximal
                angular_velocity = np.cross(segment_axis, v_relative) / segment_length
                
                # Calculate rotational kinetic energy: 0.5 * I * ω^2
                KE_rotational = 0.5 * I * np.linalg.norm(angular_velocity)**2
            else:
                KE_rotational = 0.0
            
            # Calculate potential energy: m * g * h
            # Assume z-axis is vertical
            PE = segment_mass * GRAVITY * p_com[2]
            
            # Total kinetic energy
            KE = KE_linear + KE_rotational
            
            # Store results for this segment
            energy['segments'][segment]['kinetic'][frame] = KE
            energy['segments'][segment]['potential'][frame] = PE
            energy['segments'][segment]['total'][frame] = KE + PE
            
            # Add to totals
            total_kinetic += KE
            total_potential += PE
        
        # Store total energy for this frame
        energy['total']['kinetic'].append(total_kinetic)
        energy['total']['potential'].append(total_potential)
        energy['total']['total'].append(total_kinetic + total_potential)
    
    return energy

def calculate_joint_reaction_force(
    joint_forces: Dict[str, np.ndarray],
    joint_positions: Dict[str, np.ndarray]
) -> Dict[str, Dict[str, Union[np.ndarray, float]]]:
    """
    Calculate joint reaction forces from joint forces.
    
    Args:
        joint_forces: Dictionary with joint forces
        joint_positions: Dictionary with joint positions
        
    Returns:
        Dictionary with joint reaction forces and related data
    """
    # Initialize results
    reaction_forces = {}
    
    # Identify joints where we have forces from multiple segments
    joint_map = {}
    
    # Map segment forces to joints
    for segment_name, force in joint_forces.items():
        # Extract joint names
        joints = segment_name.split('_')
        if len(joints) != 2:
            continue
            
        proximal_joint, distal_joint = joints
        
        # Add proximal force to joint map
        if proximal_joint not in joint_map:
            joint_map[proximal_joint] = []
        joint_map[proximal_joint].append((segment_name, force, 1))  # 1 for proximal end
        
        # Add distal force to joint map
        if distal_joint not in joint_map:
            joint_map[distal_joint] = []
        joint_map[distal_joint].append((segment_name, -force, -1))  # -1 for distal end (opposite direction)
    
    # Calculate reaction force at each joint
    for joint_name, forces in joint_map.items():
        if len(forces) > 1:
            # We have forces from multiple segments meeting at this joint
            total_force = np.zeros(3)
            involved_segments = []
            
            for segment_name, force, direction in forces:
                total_force += force
                involved_segments.append((segment_name, direction))
            
            # Store results
            reaction_forces[joint_name] = {
                'force': total_force,
                'magnitude': np.linalg.norm(total_force),
                'direction': total_force / np.linalg.norm(total_force) if np.linalg.norm(total_force) > 0 else np.zeros(3),
                'involved_segments': involved_segments
            }
    
    return reaction_forces

def calculate_center_of_pressure(
    force_plate_data: Dict[str, np.ndarray],
    calibration_matrix: Optional[np.ndarray] = None
) -> Dict[str, np.ndarray]:
    """
    Calculate center of pressure from force plate data.
    
    Args:
        force_plate_data: Dictionary with force plate channels (forces and moments)
        calibration_matrix: Optional calibration matrix for the force plate
        
    Returns:
        Dictionary with center of pressure and related data
    """
    # Extract force and moment data
    try:
        # Extract forces
        Fx = force_plate_data.get('Fx', np.zeros(1))
        Fy = force_plate_data.get('Fy', np.zeros(1))
        Fz = force_plate_data.get('Fz', np.zeros(1))
        
        # Extract moments
        Mx = force_plate_data.get('Mx', np.zeros(1))
        My = force_plate_data.get('My', np.zeros(1))
        Mz = force_plate_data.get('Mz', np.zeros(1))
        
        # Get dimensions
        num_samples = len(Fz)
        
        # Initialize result arrays
        cop_x = np.zeros(num_samples)
        cop_y = np.zeros(num_samples)
        
        # Apply calibration if provided
        if calibration_matrix is not None:
            # Combine raw data
            raw_data = np.column_stack((Fx, Fy, Fz, Mx, My, Mz))
            
            # Apply calibration
            calibrated = np.dot(raw_data, calibration_matrix)
            
            # Extract calibrated data
            Fx = calibrated[:, 0]
            Fy = calibrated[:, 1]
            Fz = calibrated[:, 2]
            Mx = calibrated[:, 3]
            My = calibrated[:, 4]
            Mz = calibrated[:, 5]
        
        # Calculate center of pressure for each sample
        for i in range(num_samples):
            # Check if force is significant
            if abs(Fz[i]) > 10:  # Threshold to avoid division by very small values
                # Standard equations for center of pressure
                cop_x[i] = -My[i] / Fz[i]
                cop_y[i] = Mx[i] / Fz[i]
        
        # Combine results
        result = {
            'cop_x': cop_x,
            'cop_y': cop_y,
            'force_x': Fx,
            'force_y': Fy,
            'force_z': Fz,
            'moment_x': Mx,
            'moment_y': My,
            'moment_z': Mz
        }
        
        return result
    
    except Exception as e:
        print(f"Error calculating center of pressure: {str(e)}")
        return {
            'cop_x': np.zeros(1),
            'cop_y': np.zeros(1),
            'error': str(e)
        } 