"""
Body Segment Parameters Module
-----------------------------
Functions for calculating body segment parameters including mass, center of mass,
and moments of inertia based on anthropometric data.

These implementations are based on the BodySegmentParameters.ipynb and 
CenterOfMassAndMomentOfInertia.ipynb notebooks from the BMC-master repository.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import pandas as pd
import os
import json

# Default data path - can be overridden in configuration
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                         'bolt', 'BMC-master', 'data')

# Model constants for different body segment parameter models
MODELS = {
    'Dempster-Winter': {
        'filepath': os.path.join(DATA_PATH, 'BSP_DempsterWinter.txt'),
        'landmarks_filepath': os.path.join(DATA_PATH, 'BSPlandmarks_Dempster.txt')
    },
    'Zatsiorsky-deLeva': {
        'filepath': os.path.join(DATA_PATH, 'BSP_ZdeLeva.txt'),
        'landmarks_filepath': os.path.join(DATA_PATH, 'BSPlandmarks_ZdeLeva.txt'),
        'male_filepath': os.path.join(DATA_PATH, 'BSPmale_ZdeLeva.txt'),
        'female_filepath': os.path.join(DATA_PATH, 'BSPfemale_ZdeLeva.txt')
    }
}

def load_model_data(model_name: str, gender: str = 'male') -> Dict[str, Any]:
    """
    Load body segment parameter model data.
    
    Args:
        model_name: Name of the model to use (e.g., 'Dempster-Winter', 'Zatsiorsky-deLeva')
        gender: 'male' or 'female' (only relevant for Zatsiorsky-deLeva model)
        
    Returns:
        Dictionary containing model parameters
    """
    if model_name not in MODELS:
        raise ValueError(f"Model {model_name} not supported. Choose from: {', '.join(MODELS.keys())}")
    
    model_info = MODELS[model_name]
    
    # Select the appropriate file based on gender for models that support it
    if gender == 'female' and 'female_filepath' in model_info:
        filepath = model_info['female_filepath']
    elif gender == 'male' and 'male_filepath' in model_info:
        filepath = model_info['male_filepath']
    else:
        filepath = model_info['filepath']
    
    # Check if file exists
    if not os.path.exists(filepath):
        # If file doesn't exist, fall back to embedded default data
        return _get_default_model_data(model_name, gender)
    
    # Load data from file
    try:
        df = pd.read_csv(filepath, sep='\t')
        model_data = {
            'segments': {},
            'landmarks': {}
        }
        
        # Process segment data
        for _, row in df.iterrows():
            segment_name = row['segment']
            segment_data = {}
            for col in df.columns:
                if col != 'segment':
                    segment_data[col] = row[col]
            model_data['segments'][segment_name] = segment_data
        
        # Load landmarks if available
        if 'landmarks_filepath' in model_info and os.path.exists(model_info['landmarks_filepath']):
            landmarks_df = pd.read_csv(model_info['landmarks_filepath'], sep='\t')
            for _, row in landmarks_df.iterrows():
                segment_name = row['segment']
                if 'landmarks' not in model_data:
                    model_data['landmarks'] = {}
                if segment_name not in model_data['landmarks']:
                    model_data['landmarks'][segment_name] = {}
                
                landmark_name = row['landmark']
                location = row['location']
                model_data['landmarks'][segment_name][landmark_name] = location
        
        return model_data
    except Exception as e:
        # Fall back to default data if loading fails
        print(f"Error loading model data from {filepath}: {str(e)}")
        print("Falling back to embedded default data.")
        return _get_default_model_data(model_name, gender)

def _get_default_model_data(model_name: str, gender: str) -> Dict[str, Any]:
    """
    Return embedded default data for the specified model and gender.
    This is used as a fallback when external data files aren't available.
    
    Args:
        model_name: Name of the model
        gender: 'male' or 'female'
        
    Returns:
        Dictionary with default model data
    """
    # Default data for Dempster-Winter model (taken from the original data files)
    if model_name == 'Dempster-Winter':
        return {
            'segments': {
                'Hand': {'mass': 0.006, 'COM': 0.506, 'Rg': 0.297},
                'Forearm': {'mass': 0.016, 'COM': 0.43, 'Rg': 0.303},
                'Upper arm': {'mass': 0.028, 'COM': 0.436, 'Rg': 0.322},
                'Forearm hand': {'mass': 0.022, 'COM': 0.682, 'Rg': 0.468},
                'Total arm': {'mass': 0.05, 'COM': 0.53, 'Rg': 0.368},
                'Foot': {'mass': 0.0145, 'COM': 0.5, 'Rg': 0.475},
                'Leg': {'mass': 0.0465, 'COM': 0.433, 'Rg': 0.302},
                'Thigh': {'mass': 0.1, 'COM': 0.433, 'Rg': 0.323},
                'Foot leg': {'mass': 0.061, 'COM': 0.606, 'Rg': 0.416},
                'Total leg': {'mass': 0.161, 'COM': 0.447, 'Rg': 0.326},
                'Head neck': {'mass': 0.081, 'COM': 1.0, 'Rg': 0.495},
                'Trunk': {'mass': 0.497, 'COM': 0.5, 'Rg': 0.0},
                'Trunk head neck': {'mass': 0.578, 'COM': 0.66, 'Rg': 0.503},
                'HAT': {'mass': 0.678, 'COM': 0.626, 'Rg': 0.496}
            },
            'landmarks': {
                'Foot': {'Heel': 0.0, 'Toe': 1.0},
                'Leg': {'Ankle': 0.0, 'Knee': 1.0},
                'Thigh': {'Knee': 0.0, 'Hip': 1.0}
            }
        }
    elif model_name == 'Zatsiorsky-deLeva':
        # Differentiate between male and female data
        if gender == 'male':
            return {
                'segments': {
                    'Head and neck': {'mass': 0.0694, 'COM': 0.5002, 'Rg': 0.3033},
                    'Trunk': {'mass': 0.4346, 'COM': 0.5138, 'Rg': 0.3229},
                    'Upper arm': {'mass': 0.0271, 'COM': 0.5772, 'Rg': 0.2547},
                    'Forearm': {'mass': 0.0162, 'COM': 0.4574, 'Rg': 0.2609},
                    'Hand': {'mass': 0.0061, 'COM': 0.7900, 'Rg': 0.6200},
                    'Thigh': {'mass': 0.1416, 'COM': 0.4095, 'Rg': 0.3287},
                    'Shank': {'mass': 0.0433, 'COM': 0.4459, 'Rg': 0.3023},
                    'Foot': {'mass': 0.0137, 'COM': 0.4415, 'Rg': 0.2590}
                }
            }
        else:  # female
            return {
                'segments': {
                    'Head and neck': {'mass': 0.0668, 'COM': 0.4841, 'Rg': 0.3182},
                    'Trunk': {'mass': 0.4257, 'COM': 0.5047, 'Rg': 0.3211},
                    'Upper arm': {'mass': 0.0255, 'COM': 0.5754, 'Rg': 0.2654},
                    'Forearm': {'mass': 0.0138, 'COM': 0.4559, 'Rg': 0.2671},
                    'Hand': {'mass': 0.0056, 'COM': 0.7474, 'Rg': 0.6070},
                    'Thigh': {'mass': 0.1478, 'COM': 0.3612, 'Rg': 0.3256},
                    'Shank': {'mass': 0.0481, 'COM': 0.4352, 'Rg': 0.2736},
                    'Foot': {'mass': 0.0129, 'COM': 0.4014, 'Rg': 0.2492}
                }
            }
    else:
        raise ValueError(f"No default data available for model {model_name}")

def calculate_body_segment_parameters(
    height_cm: float, 
    mass_kg: float, 
    model: str = 'Dempster-Winter',
    gender: str = 'male',
    segments: Optional[List[str]] = None,
    custom_scaling: Optional[Dict[str, float]] = None
) -> Dict[str, Dict[str, float]]:
    """
    Calculate body segment parameters based on total height and mass.
    
    Args:
        height_cm: Total body height in centimeters
        mass_kg: Total body mass in kilograms
        model: Model to use for calculations ('Dempster-Winter', 'Zatsiorsky-deLeva')
        gender: 'male' or 'female' (only for models that support gender differentiation)
        segments: List of segment names to calculate (None for all)
        custom_scaling: Optional custom scaling factors for specific segments
        
    Returns:
        Dictionary with segment parameters including masses, lengths, and inertial properties
    """
    # Load model data
    model_data = load_model_data(model, gender)
    
    # Convert height to meters
    height_m = height_cm / 100.0
    
    # Determine which segments to process
    if segments is None:
        segments_to_process = list(model_data['segments'].keys())
    else:
        segments_to_process = segments
    
    # Initialize results dictionary
    results = {
        'metadata': {
            'subject': 'Generic',
            'height_cm': height_cm,
            'height_m': height_m,
            'mass_kg': mass_kg,
            'model': model,
            'gender': gender
        },
        'segments': {}
    }
    
    # Process each segment
    for segment_name in segments_to_process:
        if segment_name not in model_data['segments']:
            print(f"Warning: Segment '{segment_name}' not found in {model} model. Skipping.")
            continue
        
        segment_data = model_data['segments'][segment_name]
        
        # Apply scaling factor if provided
        scaling_factor = 1.0
        if custom_scaling and segment_name in custom_scaling:
            scaling_factor = custom_scaling[segment_name]
        
        # Calculate segment mass
        segment_mass = segment_data['mass'] * mass_kg * scaling_factor
        
        # Calculate segment length based on height
        # Note: This is a simplification; typically more precise length calculations 
        # would be based on measured joint positions
        segment_length = height_m  # Default to full height, will be adjusted for specific segments
        
        # Adjust segment length based on specific segment
        if segment_name in ['Hand', 'Forearm', 'Upper arm', 'Total arm']:
            segment_length = height_m * 0.186  # Arm length as proportion of height
        elif segment_name in ['Foot', 'Leg', 'Thigh', 'Total leg']:
            segment_length = height_m * 0.53   # Leg length as proportion of height
        elif segment_name == 'Trunk':
            segment_length = height_m * 0.288  # Trunk length proportion
        elif segment_name == 'Head neck':
            segment_length = height_m * 0.182  # Head/neck proportion
            
        # Calculate center of mass position
        com_position = segment_data['COM'] * segment_length
        
        # Calculate radius of gyration and moment of inertia
        rg_about_com = segment_data['Rg'] * segment_length
        moment_of_inertia_com = segment_mass * (rg_about_com ** 2)
        
        # Store results for this segment
        results['segments'][segment_name] = {
            'segment_mass_kg': segment_mass,
            'segment_length_m': segment_length,
            'cm_position_m': com_position,
            'rg_about_cm_m': rg_about_com,
            'moment_of_inertia_about_cm_kgm2': moment_of_inertia_com
        }
    
    return results

def calculate_center_of_mass(
    segment_params: Dict[str, Dict[str, float]],
    joint_positions: Optional[Dict[str, np.ndarray]] = None,
    reference_frame: str = 'global'
) -> Dict[str, np.ndarray]:
    """
    Calculate the center of mass of the whole body or selected segments.
    
    Args:
        segment_params: Segment parameters from calculate_body_segment_parameters()
        joint_positions: Dictionary of joint positions (3D vectors) - if None, uses COM positions
        reference_frame: 'global' or 'local'
        
    Returns:
        Dictionary containing center of mass positions and related data
    """
    # Extract metadata
    metadata = segment_params.get('metadata', {})
    total_mass = metadata.get('mass_kg', 0)
    
    # If no total mass is available, calculate it
    if total_mass == 0:
        total_mass = sum(seg['segment_mass_kg'] for seg in segment_params['segments'].values())
    
    # Handle case when joint positions are not provided
    if joint_positions is None:
        # Use the COM positions directly from segment parameters
        com_positions = {}
        for segment_name, segment_data in segment_params['segments'].items():
            if 'cm_position_m' in segment_data:
                # Use a simple 3D vector with COM position along the z-axis
                com_positions[segment_name] = np.array([0, 0, segment_data['cm_position_m']])
    else:
        # Calculate COM positions from joint positions
        com_positions = {}
        for segment_name, segment_data in segment_params['segments'].items():
            if segment_name not in joint_positions:
                continue
                
            # Get proximal and distal joint positions
            joint_pos = joint_positions[segment_name]
            
            # Calculate the unit vector along the segment
            segment_vector = joint_pos['distal'] - joint_pos['proximal']
            segment_length = np.linalg.norm(segment_vector)
            
            if segment_length > 0:
                unit_vector = segment_vector / segment_length
            else:
                unit_vector = np.array([0, 0, 0])
                
            # Calculate COM position along the segment
            com_ratio = segment_data.get('COM', 0.5)  # Default to middle if not specified
            com_position = joint_pos['proximal'] + com_ratio * segment_vector
            
            com_positions[segment_name] = com_position
    
    # Calculate whole-body center of mass
    whole_body_com = np.zeros(3)
    mass_sum = 0
    
    for segment_name, segment_data in segment_params['segments'].items():
        if segment_name not in com_positions:
            continue
            
        segment_mass = segment_data['segment_mass_kg']
        segment_com = com_positions[segment_name]
        
        whole_body_com += segment_mass * segment_com
        mass_sum += segment_mass
    
    if mass_sum > 0:
        whole_body_com /= mass_sum
    
    # Prepare results
    results = {
        'whole_body': {
            'com_position': whole_body_com,
            'total_mass_kg': mass_sum
        },
        'segments': {
            segment_name: {
                'com_position': com_positions[segment_name],
                'mass_kg': segment_params['segments'][segment_name]['segment_mass_kg']
            }
            for segment_name in com_positions
        }
    }
    
    return results

def calculate_moment_of_inertia(
    segment_params: Dict[str, Dict[str, float]],
    joint_positions: Optional[Dict[str, Dict[str, np.ndarray]]] = None,
    axis: str = 'longitudinal'
) -> Dict[str, Dict[str, float]]:
    """
    Calculate moments of inertia for body segments.
    
    Args:
        segment_params: Segment parameters from calculate_body_segment_parameters()
        joint_positions: Dictionary of joint positions (proximal and distal joints)
        axis: Axis for inertia calculation ('longitudinal', 'transverse', 'frontal')
        
    Returns:
        Dictionary with calculated moments of inertia
    """
    results = {
        'segments': {},
        'whole_body': {}
    }
    
    # Calculate principal moments of inertia for each segment
    for segment_name, segment_data in segment_params['segments'].items():
        segment_mass = segment_data['segment_mass_kg']
        
        # Get radius of gyration about center of mass
        rg_cm = segment_data.get('rg_about_cm_m', 0)
        
        # Calculate moment of inertia about center of mass
        moi_cm = segment_mass * (rg_cm ** 2)
        
        # Store in results
        results['segments'][segment_name] = {
            'mass_kg': segment_mass,
            'moment_of_inertia_cm_kgm2': moi_cm
        }
        
        # Calculate moments of inertia about principal axes if joint positions are provided
        if joint_positions and segment_name in joint_positions:
            proximal = joint_positions[segment_name]['proximal']
            distal = joint_positions[segment_name]['distal']
            
            # Calculate segment direction vector
            direction = distal - proximal
            segment_length = np.linalg.norm(direction)
            
            if segment_length > 0:
                # Normalize direction vector
                direction = direction / segment_length
                
                # Calculate moments of inertia about principal axes
                # Longitudinal axis (along the segment)
                longitudinal_moi = segment_mass * (segment_data.get('Rg_longitudinal', 0.2) * segment_length) ** 2
                
                # Transverse axis (perpendicular to longitudinal, in the sagittal plane)
                transverse_moi = segment_mass * (segment_data.get('Rg_transverse', 0.4) * segment_length) ** 2
                
                # Frontal axis (perpendicular to longitudinal and transverse)
                frontal_moi = segment_mass * (segment_data.get('Rg_frontal', 0.4) * segment_length) ** 2
                
                results['segments'][segment_name].update({
                    'moment_of_inertia_longitudinal_kgm2': longitudinal_moi,
                    'moment_of_inertia_transverse_kgm2': transverse_moi,
                    'moment_of_inertia_frontal_kgm2': frontal_moi
                })
                
                # Set the requested axis inertia as the primary result
                if axis == 'longitudinal':
                    results['segments'][segment_name]['moment_of_inertia_kgm2'] = longitudinal_moi
                elif axis == 'transverse':
                    results['segments'][segment_name]['moment_of_inertia_kgm2'] = transverse_moi
                elif axis == 'frontal':
                    results['segments'][segment_name]['moment_of_inertia_kgm2'] = frontal_moi
    
    # Calculate whole-body moment of inertia if needed
    # This is a complex calculation based on parallel axis theorem and would require 
    # a more detailed implementation for arbitrary postures
    
    return results

def load_segment_data_from_file(filepath: str) -> Dict[str, Any]:
    """
    Load segment data from a JSON file.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        Dictionary with segment data
    """
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading segment data from {filepath}: {str(e)}")
        return {}

def save_segment_data_to_file(data: Dict[str, Any], filepath: str) -> bool:
    """
    Save segment data to a JSON file.
    
    Args:
        data: Segment data dictionary
        filepath: Output file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving segment data to {filepath}: {str(e)}")
        return False

def apply_anthropometric_scaling(
    reference_data: Dict[str, Any],
    target_height_cm: float,
    target_mass_kg: float
) -> Dict[str, Any]:
    """
    Scale segment parameters from a reference subject to a target subject.
    
    Args:
        reference_data: Segment parameters of reference subject
        target_height_cm: Height of target subject in cm
        target_mass_kg: Mass of target subject in kg
        
    Returns:
        Scaled segment parameters for target subject
    """
    # Extract reference metadata
    reference_metadata = reference_data.get('metadata', {})
    reference_height_cm = reference_metadata.get('height_cm', 170)
    reference_mass_kg = reference_metadata.get('mass_kg', 70)
    
    # Calculate scaling factors
    height_ratio = target_height_cm / reference_height_cm
    mass_ratio = target_mass_kg / reference_mass_kg
    
    # Create result structure
    result = {
        'metadata': {
            'subject': f"Scaled from {reference_metadata.get('subject', 'Unknown')}",
            'height_cm': target_height_cm,
            'height_m': target_height_cm / 100.0,
            'mass_kg': target_mass_kg,
            'model': reference_metadata.get('model', 'Unknown'),
            'scaling_reference': reference_metadata.get('subject', 'Unknown')
        },
        'segments': {}
    }
    
    # Scale each segment
    for segment_name, segment_data in reference_data.get('segments', {}).items():
        scaled_segment = {}
        
        # Scale mass by mass ratio
        if 'segment_mass_kg' in segment_data:
            scaled_segment['segment_mass_kg'] = segment_data['segment_mass_kg'] * mass_ratio
        
        # Scale length by height ratio
        if 'segment_length_m' in segment_data:
            scaled_segment['segment_length_m'] = segment_data['segment_length_m'] * height_ratio
        
        # Scale COM position by height ratio
        if 'cm_position_m' in segment_data:
            scaled_segment['cm_position_m'] = segment_data['cm_position_m'] * height_ratio
        
        # Scale radius of gyration by height ratio
        if 'rg_about_cm_m' in segment_data:
            scaled_segment['rg_about_cm_m'] = segment_data['rg_about_cm_m'] * height_ratio
        
        # Scale moment of inertia (mass * length^2)
        if 'moment_of_inertia_about_cm_kgm2' in segment_data:
            scaled_segment['moment_of_inertia_about_cm_kgm2'] = (
                segment_data['moment_of_inertia_about_cm_kgm2'] * mass_ratio * (height_ratio ** 2)
            )
        
        result['segments'][segment_name] = scaled_segment
    
    return result 