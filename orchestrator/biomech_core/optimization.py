"""
Optimization Module
-----------------
Functions for optimizing biomechanical movements, trajectories, and postures
using principles such as minimum-jerk, least action, and energy minimization.

These implementations are based on established optimization principles in 
biomechanics, motor control, and movement science.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
import scipy.optimize as optimize
import scipy.integrate as integrate
from scipy.interpolate import CubicSpline
import os
import json

# Import local modules if needed
# from . import kinematics
# from . import kinetics
# from . import muscle

# Constants
GRAVITY = 9.81  # m/s^2

def minimum_jerk_trajectory(
    start_pos: np.ndarray,
    end_pos: np.ndarray,
    start_vel: Optional[np.ndarray] = None,
    end_vel: Optional[np.ndarray] = None,
    start_acc: Optional[np.ndarray] = None,
    end_acc: Optional[np.ndarray] = None,
    duration: float = 1.0,
    time_points: Optional[np.ndarray] = None,
    normalized: bool = False
) -> Dict[str, np.ndarray]:
    """
    Generate a minimum-jerk trajectory between start and end positions.
    
    The minimum-jerk trajectory minimizes the time integral of squared jerk
    (third derivative of position), which is believed to be a principle used
    by the central nervous system for smooth movements.
    
    Args:
        start_pos: Starting position (can be 1D, 2D, or 3D)
        end_pos: Ending position (same dimensionality as start_pos)
        start_vel: Starting velocity (optional, default: zero)
        end_vel: Ending velocity (optional, default: zero)
        start_acc: Starting acceleration (optional, default: zero)
        end_acc: Ending acceleration (optional, default: zero)
        duration: Movement duration in seconds
        time_points: Optional array of time points for trajectory evaluation
        normalized: If True, return normalized time from 0 to 1 instead of seconds
        
    Returns:
        Dictionary with position, velocity, acceleration, and jerk trajectories
    """
    # Handle default boundary conditions
    if start_vel is None:
        start_vel = np.zeros_like(start_pos)
    if end_vel is None:
        end_vel = np.zeros_like(end_pos)
    if start_acc is None:
        start_acc = np.zeros_like(start_pos)
    if end_acc is None:
        end_acc = np.zeros_like(end_pos)
    
    # Check input dimensions
    if not (start_pos.shape == end_pos.shape == start_vel.shape == end_vel.shape == 
            start_acc.shape == end_acc.shape):
        raise ValueError("All position, velocity, and acceleration vectors must have the same dimensions")
    
    # Define time points
    if time_points is None:
        n_points = 100
        time_points = np.linspace(0, duration, n_points)
    
    # Normalize time to [0, 1] for calculations
    t_norm = time_points / duration
    
    # Initialize result arrays
    dimensions = start_pos.shape[0]
    positions = np.zeros((len(time_points), dimensions))
    velocities = np.zeros((len(time_points), dimensions))
    accelerations = np.zeros((len(time_points), dimensions))
    jerks = np.zeros((len(time_points), dimensions))
    
    # Calculate trajectories for each dimension
    for dim in range(dimensions):
        # Extract boundary conditions for this dimension
        x0 = start_pos[dim]
        xf = end_pos[dim]
        v0 = start_vel[dim] * duration  # Scale to normalized time
        vf = end_vel[dim] * duration
        a0 = start_acc[dim] * (duration**2)  # Scale to normalized time
        af = end_acc[dim] * (duration**2)
        
        # Calculate polynomial coefficients for minimum-jerk trajectory
        # Using 5th-order polynomial: x(t) = sum(c[i] * t^i) for i=0...5
        c = np.zeros(6)
        c[0] = x0
        c[1] = v0
        c[2] = a0 / 2
        
        # Set up system of equations for remaining coefficients
        A = np.array([
            [1, 1, 1],
            [3, 4, 5],
            [6, 12, 20]
        ])
        
        b = np.array([
            xf - x0 - v0 - a0/2,
            vf - v0 - a0,
            af - a0
        ])
        
        # Solve for c3, c4, c5
        c[3:6] = np.linalg.solve(A, b)
        
        # Calculate position, velocity, acceleration, and jerk trajectories
        for i, t in enumerate(t_norm):
            # Position: x(t)
            positions[i, dim] = sum(c[j] * (t**j) for j in range(6))
            
            # Velocity: dx/dt
            if t == 0 and v0 == 0:
                velocities[i, dim] = 0
            else:
                velocities[i, dim] = sum(j * c[j] * (t**(j-1)) for j in range(1, 6))
            
            # Acceleration: d^2x/dt^2
            if t == 0 and a0 == 0:
                accelerations[i, dim] = 0
            else:
                accelerations[i, dim] = sum(j * (j-1) * c[j] * (t**(j-2)) for j in range(2, 6))
            
            # Jerk: d^3x/dt^3
            jerks[i, dim] = sum(j * (j-1) * (j-2) * c[j] * (t**(j-3)) for j in range(3, 6))
    
    # Rescale derivatives back to original time scale if not normalized
    if not normalized:
        velocities /= duration
        accelerations /= (duration**2)
        jerks /= (duration**3)
    
    return {
        'time': time_points if not normalized else t_norm,
        'position': positions,
        'velocity': velocities,
        'acceleration': accelerations,
        'jerk': jerks
    }

def principle_of_least_action_trajectory(
    start_pos: np.ndarray,
    end_pos: np.ndarray,
    mass: float,
    duration: float,
    potential_energy_fn: Callable[[np.ndarray], float],
    constraints: Optional[List[Dict[str, Any]]] = None,
    n_points: int = 50,
    n_basis: int = 10
) -> Dict[str, np.ndarray]:
    """
    Generate a trajectory that minimizes the action (integral of Lagrangian).
    
    The principle of least action states that the path taken by a physical system
    between two states is the one that minimizes the action, which is the time
    integral of the Lagrangian (kinetic energy minus potential energy).
    
    Args:
        start_pos: Starting position (1D, 2D, or 3D)
        end_pos: Ending position (same dimensionality as start_pos)
        mass: Mass of the object/body
        duration: Movement duration in seconds
        potential_energy_fn: Function that calculates potential energy given a position
        constraints: Optional list of constraint dictionaries
        n_points: Number of points in the trajectory
        n_basis: Number of basis functions for trajectory parameterization
        
    Returns:
        Dictionary with optimized position, velocity, and energy trajectories
    """
    dimensions = len(start_pos)
    
    # Time points
    time_points = np.linspace(0, duration, n_points)
    dt = duration / (n_points - 1)
    
    # Initial trajectory: straight line
    initial_trajectory = np.zeros((n_points, dimensions))
    for dim in range(dimensions):
        initial_trajectory[:, dim] = np.linspace(start_pos[dim], end_pos[dim], n_points)
    
    # Define basis functions (using sine waves)
    def basis_function(i, t, T):
        """ith basis function evaluated at time t with period T"""
        return np.sin(i * np.pi * t / T)
    
    # Initialize coefficients for each dimension
    # We use n_basis coefficients per dimension
    initial_coeffs = np.zeros(dimensions * n_basis)
    
    # Calculate Lagrangian (T - V) for a given trajectory
    def calculate_lagrangian(trajectory, velocities):
        lagrangian = np.zeros(len(trajectory))
        for i in range(len(trajectory)):
            # Kinetic energy: 0.5 * m * v^2
            kinetic = 0.5 * mass * np.sum(velocities[i]**2)
            
            # Potential energy
            potential = potential_energy_fn(trajectory[i])
            
            # Lagrangian = T - V
            lagrangian[i] = kinetic - potential
        
        return lagrangian
    
    # Calculate action for a given trajectory
    def calculate_action(trajectory, velocities):
        lagrangian = calculate_lagrangian(trajectory, velocities)
        
        # Action is the time integral of the Lagrangian
        action = np.trapz(lagrangian, dx=dt)
        
        return -action  # Negative because we're minimizing
    
    # Generate trajectory from coefficients
    def generate_trajectory(coeffs):
        # Reshape coefficients
        coeffs = coeffs.reshape(dimensions, n_basis)
        
        # Initialize trajectory
        trajectory = np.zeros((n_points, dimensions))
        
        # Start with straight line
        for dim in range(dimensions):
            trajectory[:, dim] = np.linspace(start_pos[dim], end_pos[dim], n_points)
        
        # Add contribution from basis functions
        for dim in range(dimensions):
            for i in range(n_basis):
                basis_values = np.array([basis_function(i+1, t, duration) for t in time_points])
                
                # Scale basis function to be zero at boundaries
                basis_values[0] = 0
                basis_values[-1] = 0
                
                trajectory[:, dim] += coeffs[dim, i] * basis_values
        
        return trajectory
    
    # Calculate velocities from positions
    def calculate_velocities(trajectory):
        velocities = np.zeros_like(trajectory)
        
        # Central difference for interior points
        velocities[1:-1] = (trajectory[2:] - trajectory[:-2]) / (2 * dt)
        
        # Forward and backward differences for endpoints
        velocities[0] = (trajectory[1] - trajectory[0]) / dt
        velocities[-1] = (trajectory[-1] - trajectory[-2]) / dt
        
        return velocities
    
    # Define objective function for optimization
    def objective(coeffs):
        trajectory = generate_trajectory(coeffs)
        velocities = calculate_velocities(trajectory)
        
        # Calculate action
        action = calculate_action(trajectory, velocities)
        
        # Add constraint penalties if applicable
        penalty = 0.0
        if constraints:
            for constraint in constraints:
                constraint_type = constraint.get('type', 'position')
                constraint_dim = constraint.get('dimension', 0)
                constraint_time_idx = constraint.get('time_index', None)
                constraint_value = constraint.get('value', 0.0)
                constraint_weight = constraint.get('weight', 1000.0)
                
                if constraint_type == 'position' and constraint_time_idx is not None:
                    penalty += constraint_weight * (trajectory[constraint_time_idx, constraint_dim] - constraint_value)**2
                elif constraint_type == 'velocity' and constraint_time_idx is not None:
                    penalty += constraint_weight * (velocities[constraint_time_idx, constraint_dim] - constraint_value)**2
        
        return action + penalty
    
    # Run optimization
    result = optimize.minimize(
        objective,
        initial_coeffs,
        method='BFGS',
        options={'maxiter': 1000}
    )
    
    # Generate final trajectory
    final_trajectory = generate_trajectory(result.x)
    final_velocities = calculate_velocities(final_trajectory)
    
    # Calculate energies
    kinetic_energy = np.zeros(n_points)
    potential_energy = np.zeros(n_points)
    total_energy = np.zeros(n_points)
    
    for i in range(n_points):
        kinetic_energy[i] = 0.5 * mass * np.sum(final_velocities[i]**2)
        potential_energy[i] = potential_energy_fn(final_trajectory[i])
        total_energy[i] = kinetic_energy[i] + potential_energy[i]
    
    return {
        'time': time_points,
        'position': final_trajectory,
        'velocity': final_velocities,
        'kinetic_energy': kinetic_energy,
        'potential_energy': potential_energy,
        'total_energy': total_energy
    }

def optimize_posture(
    joint_angles: Dict[str, float],
    objective_function: Callable[[Dict[str, float]], float],
    constraints: Optional[List[Dict[str, Any]]] = None,
    joint_limits: Optional[Dict[str, Tuple[float, float]]] = None,
    method: str = 'L-BFGS-B',
    max_iterations: int = 1000
) -> Dict[str, Any]:
    """
    Optimize a biomechanical posture based on an objective function.
    
    Args:
        joint_angles: Initial joint angles dictionary
        objective_function: Function to minimize, takes joint angles as input
        constraints: Optional list of constraint dictionaries
        joint_limits: Optional dictionary of joint angle limits (min, max)
        method: Optimization method
        max_iterations: Maximum number of iterations
        
    Returns:
        Dictionary with optimized joint angles and optimization results
    """
    # Extract joint names and initial values
    joint_names = list(joint_angles.keys())
    initial_values = np.array([joint_angles[joint] for joint in joint_names])
    
    # Set up bounds if joint limits are provided
    bounds = None
    if joint_limits:
        bounds = [(joint_limits.get(joint, (None, None))[0], 
                   joint_limits.get(joint, (None, None))[1]) 
                  for joint in joint_names]
    
    # Define objective function for optimizer
    def objective(x):
        # Convert array back to dictionary
        angles = {joint_names[i]: x[i] for i in range(len(joint_names))}
        
        # Call provided objective function
        obj_value = objective_function(angles)
        
        # Add constraint penalties if applicable
        penalty = 0.0
        if constraints:
            for constraint in constraints:
                constraint_type = constraint.get('type', 'joint_angle')
                constraint_joint = constraint.get('joint', '')
                constraint_value = constraint.get('value', 0.0)
                constraint_weight = constraint.get('weight', 1000.0)
                
                if constraint_type == 'joint_angle' and constraint_joint in angles:
                    penalty += constraint_weight * (angles[constraint_joint] - constraint_value)**2
        
        return obj_value + penalty
    
    # Run optimization
    result = optimize.minimize(
        objective,
        initial_values,
        method=method,
        bounds=bounds,
        options={'maxiter': max_iterations}
    )
    
    # Convert result back to dictionary
    optimized_angles = {joint_names[i]: result.x[i] for i in range(len(joint_names))}
    
    return {
        'joint_angles': optimized_angles,
        'objective_value': result.fun,
        'success': result.success,
        'message': result.message,
        'n_iterations': result.nit if hasattr(result, 'nit') else None
    }

def minimize_joint_loads(
    joint_angles: Dict[str, float],
    body_parameters: Dict[str, Any],
    external_loads: Optional[Dict[str, np.ndarray]] = None,
    joint_limits: Optional[Dict[str, Tuple[float, float]]] = None,
    joint_weights: Optional[Dict[str, float]] = None,
    max_iterations: int = 1000
) -> Dict[str, Any]:
    """
    Find an optimal posture that minimizes joint loads/moments.
    
    Args:
        joint_angles: Initial joint angles dictionary
        body_parameters: Dictionary with body segment parameters
        external_loads: Optional dictionary of external loads
        joint_limits: Optional dictionary of joint angle limits
        joint_weights: Optional dictionary of weights for each joint
        max_iterations: Maximum number of iterations
        
    Returns:
        Dictionary with optimized joint angles and joint loads
    """
    # Set default joint weights if not provided
    if joint_weights is None:
        joint_weights = {joint: 1.0 for joint in joint_angles.keys()}
    
    # Define objective function: sum of weighted joint moments
    def objective_function(angles):
        # This is a placeholder for a more complex function that would:
        # 1. Calculate joint positions from angles (forward kinematics)
        # 2. Calculate joint loads using static or dynamic analysis
        # 3. Return a weighted sum of joint loads
        
        # For demonstration, we'll use a simple proxy: 
        # The sum of absolute joint angles weighted by joint_weights
        # In a real application, this would be replaced by actual biomechanical calculations
        return sum(joint_weights.get(joint, 1.0) * abs(angle) for joint, angle in angles.items())
    
    # Run the optimization
    result = optimize_posture(
        joint_angles,
        objective_function,
        joint_limits=joint_limits,
        max_iterations=max_iterations
    )
    
    # In a real application, calculate actual joint loads with the optimized posture
    # For demonstration, we just return the optimization result
    return result

def maximize_performance(
    joint_angles: Dict[str, float],
    performance_metric: Callable[[Dict[str, float]], float],
    body_parameters: Dict[str, Any],
    joint_limits: Optional[Dict[str, Tuple[float, float]]] = None,
    constraints: Optional[List[Dict[str, Any]]] = None,
    max_iterations: int = 1000
) -> Dict[str, Any]:
    """
    Find an optimal posture that maximizes a performance metric.
    
    Args:
        joint_angles: Initial joint angles dictionary
        performance_metric: Function that calculates performance (higher is better)
        body_parameters: Dictionary with body segment parameters
        joint_limits: Optional dictionary of joint angle limits
        constraints: Optional list of constraint dictionaries
        max_iterations: Maximum number of iterations
        
    Returns:
        Dictionary with optimized joint angles and performance value
    """
    # Define objective function (negative of performance because we're minimizing)
    def objective_function(angles):
        return -performance_metric(angles)
    
    # Run the optimization
    result = optimize_posture(
        joint_angles,
        objective_function,
        constraints=constraints,
        joint_limits=joint_limits,
        max_iterations=max_iterations
    )
    
    # Convert back to performance (positive value)
    result['performance_value'] = -result['objective_value']
    del result['objective_value']
    
    return result

def trajectory_discretization(
    start: Dict[str, float],
    end: Dict[str, float],
    n_points: int = 50,
    method: str = 'linear'
) -> Dict[str, List[float]]:
    """
    Discretize a trajectory between start and end states.
    
    Args:
        start: Dictionary of starting joint angles
        end: Dictionary of ending joint angles
        n_points: Number of points in the discretized trajectory
        method: Interpolation method ('linear', 'minimum_jerk', 'cubic')
        
    Returns:
        Dictionary mapping joint names to lists of angle values
    """
    # Get joint names
    joint_names = list(start.keys())
    
    # Initialize result
    trajectory = {joint: np.zeros(n_points) for joint in joint_names}
    
    # Create time points
    time_points = np.linspace(0, 1, n_points)
    
    for joint in joint_names:
        if method == 'linear':
            # Linear interpolation
            trajectory[joint] = start[joint] + (end[joint] - start[joint]) * time_points
        
        elif method == 'minimum_jerk':
            # Minimum jerk interpolation
            t = time_points
            t3 = t**3
            t4 = t**4
            t5 = t**5
            
            # 5th order polynomial for minimum jerk
            trajectory[joint] = start[joint] + (end[joint] - start[joint]) * (10*t3 - 15*t4 + 6*t5)
        
        elif method == 'cubic':
            # Cubic interpolation with zero velocity at endpoints
            t = time_points
            t2 = t**2
            t3 = t**3
            
            # Cubic polynomial with zero velocity at endpoints
            trajectory[joint] = start[joint] + (end[joint] - start[joint]) * (3*t2 - 2*t3)
        
        else:
            raise ValueError(f"Unknown method: {method}")
    
    return trajectory

def cost_of_transport(
    trajectory: Dict[str, np.ndarray],
    velocities: Dict[str, np.ndarray],
    mass: float,
    energy_fn: Callable[[Dict[str, float], Dict[str, float]], float],
    distance: float,
    time_step: float
) -> float:
    """
    Calculate the energetic cost of transport for a movement trajectory.
    
    Args:
        trajectory: Dictionary mapping joint names to position arrays
        velocities: Dictionary mapping joint names to velocity arrays
        mass: Body mass in kg
        energy_fn: Function that calculates energy expenditure rate
        distance: Total distance traveled in meters
        time_step: Time step between trajectory points in seconds
        
    Returns:
        Cost of transport (energy per unit mass per unit distance)
    """
    # Get number of time points
    n_points = len(next(iter(trajectory.values())))
    
    # Calculate energy expenditure at each time point
    energy_rate = np.zeros(n_points)
    for i in range(n_points):
        # Extract position and velocity at current time point
        pos = {joint: trajectory[joint][i] for joint in trajectory}
        vel = {joint: velocities[joint][i] for joint in velocities}
        
        # Calculate energy rate
        energy_rate[i] = energy_fn(pos, vel)
    
    # Calculate total energy by integrating energy rate over time
    total_energy = np.trapz(energy_rate, dx=time_step)
    
    # Calculate cost of transport
    cot = total_energy / (mass * distance)
    
    return cot

def optimality_index_jerk(trajectory: Dict[str, np.ndarray], time_step: float) -> float:
    """
    Calculate the optimality index based on jerk minimization.
    
    Args:
        trajectory: Dictionary mapping joint names to position arrays
        time_step: Time step between trajectory points in seconds
        
    Returns:
        Optimality index (lower is better)
    """
    total_squared_jerk = 0.0
    
    for joint, positions in trajectory.items():
        # Calculate velocities using central differences
        velocities = np.gradient(positions, time_step)
        
        # Calculate accelerations
        accelerations = np.gradient(velocities, time_step)
        
        # Calculate jerk
        jerk = np.gradient(accelerations, time_step)
        
        # Accumulate squared jerk
        total_squared_jerk += np.sum(jerk**2)
    
    # Normalize by number of joints and trajectory duration
    n_joints = len(trajectory)
    duration = time_step * (len(next(iter(trajectory.values()))) - 1)
    
    optimality_index = total_squared_jerk / (n_joints * duration)
    
    return optimality_index

def minimum_jerk_control(
    current_state: np.ndarray,
    target_state: np.ndarray,
    duration: float,
    dt: float,
    state_dim: int = 3  # position, velocity, acceleration
) -> Dict[str, np.ndarray]:
    """
    Generate optimal control signals based on minimum jerk principle.
    
    Args:
        current_state: Current system state [pos, vel, acc]
        target_state: Target system state [pos, vel, acc]
        duration: Movement duration in seconds
        dt: Time step for control signals
        state_dim: Dimension of the state (3 for [pos, vel, acc])
        
    Returns:
        Dictionary with control signals and predicted state trajectories
    """
    # Number of points in the trajectory
    n_points = int(duration / dt) + 1
    
    # Time points
    time_points = np.linspace(0, duration, n_points)
    
    # Generate minimum jerk trajectory
    dimensions = len(current_state) // state_dim
    
    # Extract state components
    current_pos = current_state[:dimensions]
    current_vel = current_state[dimensions:2*dimensions]
    current_acc = current_state[2*dimensions:3*dimensions]
    
    target_pos = target_state[:dimensions]
    target_vel = target_state[dimensions:2*dimensions]
    target_acc = target_state[2*dimensions:3*dimensions]
    
    # Generate trajectory
    traj = minimum_jerk_trajectory(
        current_pos,
        target_pos,
        current_vel,
        target_vel,
        current_acc,
        target_acc,
        duration,
        time_points
    )
    
    # Extract position, velocity, acceleration trajectories
    positions = traj['position']
    velocities = traj['velocity']
    accelerations = traj['acceleration']
    jerks = traj['jerk']
    
    # In a more complex model, control signals would be derived from these
    # For this simple example, we'll use jerk as the control signal
    control_signals = jerks
    
    return {
        'time': time_points,
        'position': positions,
        'velocity': velocities,
        'acceleration': accelerations,
        'jerk': jerks,
        'control': control_signals
    }

def save_trajectory(trajectory: Dict[str, Any], filepath: str) -> bool:
    """
    Save trajectory data to a JSON file.
    
    Args:
        trajectory: Trajectory data dictionary
        filepath: Output file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert numpy arrays to lists for JSON serialization
        serializable = {}
        for key, value in trajectory.items():
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
        print(f"Error saving trajectory to {filepath}: {str(e)}")
        return False

def load_trajectory(filepath: str) -> Dict[str, Any]:
    """
    Load trajectory data from a JSON file.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        Trajectory data dictionary
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Convert lists back to numpy arrays where appropriate
        trajectory = {}
        for key, value in data.items():
            if isinstance(value, list):
                # Check if it's a list of lists (2D array)
                if value and isinstance(value[0], list):
                    trajectory[key] = np.array(value)
                else:
                    trajectory[key] = np.array(value)
            elif isinstance(value, dict):
                trajectory[key] = {}
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list):
                        if sub_value and isinstance(sub_value[0], list):
                            trajectory[key][sub_key] = np.array(sub_value)
                        else:
                            trajectory[key][sub_key] = np.array(sub_value)
                    else:
                        trajectory[key][sub_key] = sub_value
            else:
                trajectory[key] = value
        
        return trajectory
    except Exception as e:
        print(f"Error loading trajectory from {filepath}: {str(e)}")
        return {} 