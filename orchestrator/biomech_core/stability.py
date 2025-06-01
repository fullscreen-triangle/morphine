"""
Stability Module
--------------
Functions for analyzing postural stability, balance, and equilibrium
using stabilography and biomechanical principles.

These implementations are based on established methods in balance assessment,
postural control, and clinical stabilometry.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
import scipy.stats as stats
import scipy.signal as signal
import os
import json

# Constants
GRAVITY = 9.81  # m/s^2

def calculate_cop_from_force_plate(
    forces: np.ndarray,
    moments: np.ndarray,
    origin_height: float = 0.0
) -> np.ndarray:
    """
    Calculate Center of Pressure (CoP) from force plate data.
    
    Args:
        forces: Force data with shape [n_samples, 3] for Fx, Fy, Fz
        moments: Moment data with shape [n_samples, 3] for Mx, My, Mz
        origin_height: Height of the force plate origin above the surface
        
    Returns:
        CoP coordinates with shape [n_samples, 2] for x, y positions
    """
    # Ensure forces and moments are numpy arrays
    forces = np.asarray(forces)
    moments = np.asarray(moments)
    
    # Extract components
    fx = forces[:, 0]
    fy = forces[:, 1]
    fz = forces[:, 2]
    
    mx = moments[:, 0]
    my = moments[:, 1]
    
    # Calculate CoP coordinates
    # Handle division by zero (when no vertical force)
    eps = 1e-10
    fz_safe = np.where(np.abs(fz) > eps, fz, eps)
    
    # CoP formulas
    cop_x = -my / fz_safe - fx * origin_height / fz_safe
    cop_y = mx / fz_safe - fy * origin_height / fz_safe
    
    # Combine into a single array
    cop = np.column_stack((cop_x, cop_y))
    
    return cop

def calculate_stability_metrics(
    cop_data: np.ndarray,
    time_data: Optional[np.ndarray] = None,
    sampling_rate: Optional[float] = None
) -> Dict[str, float]:
    """
    Calculate various stability metrics from Center of Pressure (CoP) data.
    
    Args:
        cop_data: CoP data with shape [n_samples, 2] for x, y positions
        time_data: Optional time points corresponding to CoP data
        sampling_rate: Sampling rate in Hz (required if time_data is not provided)
        
    Returns:
        Dictionary with calculated stability metrics
    """
    # Set up time data if not provided
    if time_data is None:
        if sampling_rate is None:
            raise ValueError("Either time_data or sampling_rate must be provided")
        n_samples = cop_data.shape[0]
        time_data = np.arange(n_samples) / sampling_rate
    
    # Extract x and y components
    cop_x = cop_data[:, 0]
    cop_y = cop_data[:, 1]
    
    # Calculate time step (assuming uniform sampling)
    dt = np.mean(np.diff(time_data))
    
    # Calculate CoP velocities
    vel_x = np.diff(cop_x) / dt
    vel_y = np.diff(cop_y) / dt
    
    # Add zero at the beginning to maintain array size
    vel_x = np.concatenate([[0], vel_x])
    vel_y = np.concatenate([[0], vel_y])
    
    # Calculate CoP speed (magnitude of velocity)
    speed = np.sqrt(vel_x**2 + vel_y**2)
    
    # Calculate metrics
    
    # 1. Mean position
    mean_x = np.mean(cop_x)
    mean_y = np.mean(cop_y)
    
    # 2. Standard deviation
    std_x = np.std(cop_x)
    std_y = np.std(cop_y)
    
    # 3. Range
    range_x = np.max(cop_x) - np.min(cop_x)
    range_y = np.max(cop_y) - np.min(cop_y)
    
    # 4. Path length
    path_length = np.sum(np.sqrt(np.diff(cop_x)**2 + np.diff(cop_y)**2))
    
    # 5. Mean velocity
    mean_velocity = path_length / (time_data[-1] - time_data[0])
    
    # 6. Mean speed (magnitude of velocity)
    mean_speed = np.mean(speed)
    
    # 7. Area metrics
    
    # 7.1 95% confidence ellipse area
    # Calculate covariance matrix
    cov_matrix = np.cov(cop_x, cop_y)
    
    # Calculate eigenvalues and eigenvectors
    eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)
    
    # Sort eigenvalues and eigenvectors
    idx = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    
    # Calculate semi-major and semi-minor axes
    chi2_val = stats.chi2.ppf(0.95, 2)  # 95% confidence with 2 DOF
    semi_major = np.sqrt(chi2_val * eigenvalues[0])
    semi_minor = np.sqrt(chi2_val * eigenvalues[1])
    
    # Calculate ellipse area
    ellipse_area = np.pi * semi_major * semi_minor
    
    # 7.2 Convex hull area
    try:
        from scipy.spatial import ConvexHull
        hull = ConvexHull(cop_data)
        convex_hull_area = hull.volume  # In 2D, volume is area
    except:
        # Fallback if ConvexHull is not available
        convex_hull_area = None
    
    # Compile all metrics
    metrics = {
        'mean_x': mean_x,
        'mean_y': mean_y,
        'std_x': std_x,
        'std_y': std_y,
        'range_x': range_x,
        'range_y': range_y,
        'path_length': path_length,
        'mean_velocity': mean_velocity,
        'mean_speed': mean_speed,
        'ellipse_area': ellipse_area,
        'convex_hull_area': convex_hull_area
    }
    
    return metrics

def calculate_stability_index(
    cop_data: np.ndarray,
    time_data: Optional[np.ndarray] = None,
    sampling_rate: Optional[float] = None,
    base_of_support: Optional[np.ndarray] = None,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate a composite stability index from CoP data.
    
    Args:
        cop_data: CoP data with shape [n_samples, 2] for x, y positions
        time_data: Optional time points corresponding to CoP data
        sampling_rate: Sampling rate in Hz (required if time_data is not provided)
        base_of_support: Optional polygon defining the base of support
        weights: Optional dictionary of weights for different metrics
        
    Returns:
        Stability index (higher values indicate less stability)
    """
    # Get stability metrics
    metrics = calculate_stability_metrics(cop_data, time_data, sampling_rate)
    
    # Set default weights if not provided
    if weights is None:
        weights = {
            'std_x': 0.2,
            'std_y': 0.2,
            'path_length': 0.3,
            'ellipse_area': 0.3
        }
    
    # Normalize metrics to base of support if provided
    if base_of_support is not None:
        # Calculate base of support dimensions
        bos_x_range = np.max(base_of_support[:, 0]) - np.min(base_of_support[:, 0])
        bos_y_range = np.max(base_of_support[:, 1]) - np.min(base_of_support[:, 1])
        bos_area = np.abs(np.sum(base_of_support[:-1, 0] * base_of_support[1:, 1] - 
                                 base_of_support[1:, 0] * base_of_support[:-1, 1]) / 2)
        
        # Normalize metrics
        if 'std_x' in metrics and bos_x_range > 0:
            metrics['std_x'] /= bos_x_range
        if 'std_y' in metrics and bos_y_range > 0:
            metrics['std_y'] /= bos_y_range
        if 'ellipse_area' in metrics and bos_area > 0:
            metrics['ellipse_area'] /= bos_area
    
    # Calculate weighted stability index
    stability_index = 0.0
    for metric, weight in weights.items():
        if metric in metrics and metrics[metric] is not None:
            stability_index += weight * metrics[metric]
    
    return stability_index

def calculate_limits_of_stability(
    com_position: np.ndarray,
    base_of_support: np.ndarray,
    height: float,
    mass: float,
    gravity: float = GRAVITY
) -> Dict[str, Any]:
    """
    Calculate limits of stability based on center of mass position and base of support.
    
    Args:
        com_position: Center of mass position [x, y, z]
        base_of_support: Polygon defining the base of support with shape [n_vertices, 2]
        height: Height of the center of mass from the ground
        mass: Body mass in kg
        gravity: Gravitational acceleration (default: 9.81 m/s^2)
        
    Returns:
        Dictionary with limits of stability metrics
    """
    # Extract CoM horizontal position
    com_x, com_y = com_position[0], com_position[1]
    
    # Calculate distances from CoM to each edge of the base of support
    n_vertices = base_of_support.shape[0]
    distances = np.zeros(n_vertices)
    
    for i in range(n_vertices):
        # Get current and next vertex
        v1 = base_of_support[i]
        v2 = base_of_support[(i + 1) % n_vertices]
        
        # Calculate edge vector
        edge = v2 - v1
        
        # Calculate vector from vertex to CoM
        to_com = np.array([com_x, com_y]) - v1
        
        # Calculate distance from CoM to edge
        edge_length = np.linalg.norm(edge)
        if edge_length > 0:
            # Unit vector along the edge
            edge_unit = edge / edge_length
            
            # Distance along the edge
            distance_along = np.dot(to_com, edge_unit)
            
            # Clamp to edge length
            distance_along = min(max(distance_along, 0), edge_length)
            
            # Point on the edge closest to CoM
            closest_point = v1 + distance_along * edge_unit
            
            # Distance from CoM to closest point
            distances[i] = np.linalg.norm(np.array([com_x, com_y]) - closest_point)
        else:
            # If vertices are identical, use distance to vertex
            distances[i] = np.linalg.norm(to_com)
    
    # Find minimum distance (closest edge)
    min_distance = np.min(distances)
    min_distance_idx = np.argmin(distances)
    
    # Calculate maximum theoretical lean angle before losing stability
    # tan(theta) = distance / height
    max_lean_angle = np.arctan2(min_distance, height)
    max_lean_angle_deg = np.degrees(max_lean_angle)
    
    # Calculate stability margin (as percentage of height)
    stability_margin = min_distance / height * 100.0
    
    # Calculate potential energy required to reach limit of stability
    # Potential energy = m * g * h * (1 - cos(theta))
    energy_to_limit = mass * gravity * height * (1 - np.cos(max_lean_angle))
    
    # Compile results
    results = {
        'min_distance_to_edge': min_distance,
        'max_lean_angle_rad': max_lean_angle,
        'max_lean_angle_deg': max_lean_angle_deg,
        'stability_margin_percent': stability_margin,
        'energy_to_limit_joules': energy_to_limit,
        'closest_edge_index': min_distance_idx
    }
    
    return results

def romberg_quotient(
    cop_data: np.ndarray,
    time_data: np.ndarray,
    condition_eyes_open: np.ndarray,
    condition_eyes_closed: np.ndarray
) -> Dict[str, float]:
    """
    Calculate Romberg quotient for balance assessment.
    
    The Romberg quotient is the ratio of a stability metric between
    eyes closed and eyes open conditions.
    
    Args:
        cop_data: CoP data with shape [n_samples, 2] for x, y positions
        time_data: Time points corresponding to CoP data
        condition_eyes_open: Boolean mask for eyes open condition
        condition_eyes_closed: Boolean mask for eyes closed condition
        
    Returns:
        Dictionary with Romberg quotients for different metrics
    """
    # Calculate stability metrics for each condition
    metrics_eo = calculate_stability_metrics(
        cop_data[condition_eyes_open],
        time_data[condition_eyes_open]
    )
    
    metrics_ec = calculate_stability_metrics(
        cop_data[condition_eyes_closed],
        time_data[condition_eyes_closed]
    )
    
    # Calculate Romberg quotients
    romberg = {}
    
    for metric in metrics_eo:
        if metric in metrics_ec and metrics_eo[metric] is not None and metrics_ec[metric] is not None and metrics_eo[metric] > 0:
            romberg[f"romberg_{metric}"] = metrics_ec[metric] / metrics_eo[metric]
    
    return romberg

def approximate_entropy(
    time_series: np.ndarray,
    m: int = 2,
    r: float = 0.2
) -> float:
    """
    Calculate approximate entropy (ApEn) for a time series.
    
    ApEn quantifies the unpredictability of fluctuations in a time series.
    Higher values indicate more complexity/irregularity.
    
    Args:
        time_series: 1D time series data
        m: Embedding dimension
        r: Tolerance (typically 0.1 to 0.25 * std)
        
    Returns:
        Approximate entropy value
    """
    # Ensure time_series is a 1D array
    time_series = np.ravel(time_series)
    
    # If r is provided as a proportion of std, convert to absolute
    if r < 1:
        r = r * np.std(time_series)
    
    # Get length of time series
    N = len(time_series)
    
    if N < m + 1:
        return 0.0
    
    # Initialize count arrays
    count_m = np.zeros(N - m + 1)
    count_m1 = np.zeros(N - m)
    
    # Create embedded vectors of length m and m+1
    for i in range(N - m + 1):
        # Extract vector of length m
        vec_m_i = time_series[i:i+m]
        
        for j in range(N - m + 1):
            # Extract comparison vector of length m
            vec_m_j = time_series[j:j+m]
            
            # Check if vectors are similar
            if np.max(np.abs(vec_m_i - vec_m_j)) <= r:
                count_m[i] += 1
                
                # Also check m+1 similarity if applicable
                if i < N - m and j < N - m:
                    if np.abs(time_series[i+m] - time_series[j+m]) <= r:
                        count_m1[i] += 1
    
    # Normalize counts and calculate logarithms
    count_m = count_m / (N - m + 1)
    count_m1 = count_m1 / (N - m + 1)
    
    # Avoid log(0)
    count_m[count_m <= 0] = 1e-10
    count_m1[count_m1 <= 0] = 1e-10
    
    # Calculate phi values
    phi_m = np.sum(np.log(count_m)) / (N - m + 1)
    phi_m1 = np.sum(np.log(count_m1)) / (N - m)
    
    # Calculate approximate entropy
    apen = phi_m - phi_m1
    
    return apen

def detrended_fluctuation_analysis(
    time_series: np.ndarray,
    scales: Optional[np.ndarray] = None,
    overlap: float = 0.5
) -> Dict[str, Any]:
    """
    Perform detrended fluctuation analysis (DFA) on time series data.
    
    DFA quantifies long-range temporal correlations in a signal.
    
    Args:
        time_series: 1D time series data
        scales: Array of window sizes to analyze
        overlap: Fraction of overlap between windows
        
    Returns:
        Dictionary with DFA results
    """
    # Ensure time_series is a 1D array
    time_series = np.ravel(time_series)
    
    # Remove mean
    time_series = time_series - np.mean(time_series)
    
    # Generate scales if not provided
    N = len(time_series)
    if scales is None:
        # Generate logarithmically spaced scales
        min_scale = 10  # Minimum window size
        max_scale = N // 10  # Maximum window size (1/10 of signal length)
        n_scales = 10  # Number of scales to analyze
        
        scales = np.unique(np.round(np.logspace(
            np.log10(min_scale), np.log10(max_scale), n_scales
        )).astype(int))
    
    # Integrate the signal (convert to random walk)
    walk = np.cumsum(time_series)
    
    # Initialize fluctuation function
    F = np.zeros(len(scales))
    
    # Calculate F(n) for each scale
    for i, scale in enumerate(scales):
        # Skip if scale is too large
        if scale > N // 4:
            F[i] = np.nan
            continue
        
        # Calculate number of windows
        stride = int(scale * (1 - overlap))
        if stride < 1:
            stride = 1
        
        n_windows = (N - scale) // stride + 1
        
        # Initialize detrended variance
        var = 0.0
        count = 0
        
        # Process each window
        for j in range(n_windows):
            # Extract window
            start = j * stride
            end = start + scale
            
            if end > N:
                break
                
            # Extract segment
            segment = walk[start:end]
            
            # Calculate trend (linear fit)
            x = np.arange(scale)
            coeffs = np.polyfit(x, segment, 1)
            trend = np.polyval(coeffs, x)
            
            # Detrend
            detrended = segment - trend
            
            # Calculate variance
            var += np.sum(detrended**2)
            count += 1
        
        # Calculate fluctuation function for this scale
        if count > 0:
            F[i] = np.sqrt(var / (count * scale))
    
    # Remove NaN values
    valid = ~np.isnan(F)
    scales_valid = scales[valid]
    F_valid = F[valid]
    
    # Calculate scaling exponent (alpha) using log-log fit
    if len(scales_valid) > 1:
        log_scales = np.log(scales_valid)
        log_F = np.log(F_valid)
        
        # Linear fit
        coeffs = np.polyfit(log_scales, log_F, 1)
        alpha = coeffs[0]  # Scaling exponent
        intercept = coeffs[1]
        
        # Calculate fit line
        fit_line = np.exp(intercept) * scales_valid**alpha
    else:
        alpha = np.nan
        fit_line = np.array([])
    
    # Compile results
    results = {
        'scales': scales_valid,
        'fluctuation': F_valid,
        'alpha': alpha,
        'fit_line': fit_line
    }
    
    return results

def sway_density_analysis(
    cop_data: np.ndarray,
    time_data: np.ndarray,
    radius: float = 2.0  # mm
) -> Dict[str, Any]:
    """
    Perform sway density analysis on Center of Pressure data.
    
    Identifies regions where CoP moves slowly or stays within a small area.
    
    Args:
        cop_data: CoP data with shape [n_samples, 2] for x, y positions (in mm)
        time_data: Time points corresponding to CoP data
        radius: Radius for sway density calculation (in mm)
        
    Returns:
        Dictionary with sway density results
    """
    # Get number of samples
    n_samples = cop_data.shape[0]
    
    # Initialize sway density curve
    sway_density = np.zeros(n_samples)
    
    # Calculate sway density at each point
    for i in range(n_samples):
        # Calculate distance from current point to all other points
        distances = np.sqrt(np.sum((cop_data - cop_data[i])**2, axis=1))
        
        # Count points within radius
        sway_density[i] = np.sum(distances <= radius)
    
    # Find peaks in sway density (areas of stability)
    peaks, _ = signal.find_peaks(sway_density, height=np.mean(sway_density))
    
    # Calculate peak properties
    peak_heights = sway_density[peaks]
    
    # Calculate mean peak properties
    if len(peaks) > 0:
        mean_peak_height = np.mean(peak_heights)
        
        # Calculate mean peak distance
        if len(peaks) > 1:
            peak_distances = np.diff(peaks)
            mean_peak_distance = np.mean(peak_distances)
        else:
            mean_peak_distance = n_samples
    else:
        mean_peak_height = 0
        mean_peak_distance = n_samples
    
    # Calculate sway density parameters
    mean_sway_density = np.mean(sway_density)
    max_sway_density = np.max(sway_density)
    
    # Convert peak distances to time
    if len(peaks) > 1:
        peak_times = time_data[peaks]
        mean_time_between_peaks = np.mean(np.diff(peak_times))
    else:
        mean_time_between_peaks = time_data[-1] - time_data[0]
    
    # Compile results
    results = {
        'sway_density': sway_density,
        'peak_indices': peaks,
        'peak_heights': peak_heights,
        'mean_peak_height': mean_peak_height,
        'mean_peak_distance_samples': mean_peak_distance,
        'mean_time_between_peaks': mean_time_between_peaks,
        'mean_sway_density': mean_sway_density,
        'max_sway_density': max_sway_density
    }
    
    return results

def save_stability_data(data: Dict[str, Any], filepath: str) -> bool:
    """
    Save stability analysis data to a JSON file.
    
    Args:
        data: Stability data dictionary
        filepath: Output file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert numpy arrays to lists for JSON serialization
        serializable = {}
        for key, value in data.items():
            if isinstance(value, np.ndarray):
                serializable[key] = value.tolist()
            elif isinstance(value, dict):
                serializable[key] = {}
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, np.ndarray):
                        serializable[key][sub_key] = sub_value.tolist()
                    else:
                        serializable[key][sub_key] = sub_value
            else:
                serializable[key] = value
        
        with open(filepath, 'w') as f:
            json.dump(serializable, f, indent=4)
            
        return True
    except Exception as e:
        print(f"Error saving stability data to {filepath}: {str(e)}")
        return False

def load_stability_data(filepath: str) -> Dict[str, Any]:
    """
    Load stability analysis data from a JSON file.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        Stability data dictionary
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Convert lists back to numpy arrays where appropriate
        stability_data = {}
        for key, value in data.items():
            if isinstance(value, list):
                # Check if it's a list of lists (2D array)
                if value and isinstance(value[0], list):
                    stability_data[key] = np.array(value)
                else:
                    stability_data[key] = np.array(value)
            elif isinstance(value, dict):
                stability_data[key] = {}
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list):
                        if sub_value and isinstance(sub_value[0], list):
                            stability_data[key][sub_key] = np.array(sub_value)
                        else:
                            stability_data[key][sub_key] = np.array(sub_value)
                    else:
                        stability_data[key][sub_key] = sub_value
            else:
                stability_data[key] = value
        
        return stability_data
    except Exception as e:
        print(f"Error loading stability data from {filepath}: {str(e)}")
        return {} 