"""
Muscle Module
------------
Functions for modeling muscle dynamics, activation, and force production
for biomechanical simulations.

These implementations are based on established muscle models such as Hill-type
muscle models, activation dynamics, and force-length-velocity relationships.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import scipy.optimize as optimize
import scipy.integrate as integrate
import os
import json

# Constants
MAX_ISOMETRIC_STRESS = 0.3e6  # Maximum isometric stress in N/m^2
DENSITY = 1060  # Muscle density in kg/m^3
SPECIFIC_TENSION = 25  # Specific tension in N/cm^2
PENNATION_FACTOR = 0.85  # Adjustment for pennation angle

class MuscleParameters:
    """Class containing parameters for a Hill-type muscle model."""
    
    def __init__(
        self,
        name: str,
        optimal_fiber_length: float,
        max_isometric_force: float,
        tendon_slack_length: float,
        pennation_angle: float = 0.0,
        max_contraction_velocity: Optional[float] = None,
        activation_time_constant: float = 0.01,
        deactivation_time_constant: float = 0.04,
        force_length_curve: Optional[Dict[str, List[float]]] = None,
        force_velocity_curve: Optional[Dict[str, List[float]]] = None
    ):
        """
        Initialize muscle parameters.
        
        Args:
            name: Muscle name
            optimal_fiber_length: Optimal fiber length in meters
            max_isometric_force: Maximum isometric force in Newtons
            tendon_slack_length: Tendon slack length in meters
            pennation_angle: Pennation angle in radians
            max_contraction_velocity: Maximum contraction velocity in m/s
            activation_time_constant: Time constant for activation in seconds
            deactivation_time_constant: Time constant for deactivation in seconds
            force_length_curve: Custom force-length relationship
            force_velocity_curve: Custom force-velocity relationship
        """
        self.name = name
        self.optimal_fiber_length = optimal_fiber_length
        self.max_isometric_force = max_isometric_force
        self.tendon_slack_length = tendon_slack_length
        self.pennation_angle = pennation_angle
        
        # Default max contraction velocity is 10 optimal fiber lengths per second
        if max_contraction_velocity is None:
            self.max_contraction_velocity = 10 * optimal_fiber_length
        else:
            self.max_contraction_velocity = max_contraction_velocity
            
        self.activation_time_constant = activation_time_constant
        self.deactivation_time_constant = deactivation_time_constant
        
        # Initialize default force-length curve if not provided
        if force_length_curve is None:
            self.force_length_curve = self._default_force_length_curve()
        else:
            self.force_length_curve = force_length_curve
            
        # Initialize default force-velocity curve if not provided
        if force_velocity_curve is None:
            self.force_velocity_curve = self._default_force_velocity_curve()
        else:
            self.force_velocity_curve = force_velocity_curve
    
    def _default_force_length_curve(self) -> Dict[str, List[float]]:
        """Generate default force-length curve based on standard models."""
        # Default curve: x values are normalized fiber lengths, y values are force scaling factors
        x = np.linspace(0.4, 1.6, 100)
        y = np.exp(-((x - 1.0) / 0.4) ** 2)
        
        return {'x': x.tolist(), 'y': y.tolist()}
    
    def _default_force_velocity_curve(self) -> Dict[str, List[float]]:
        """Generate default force-velocity curve based on Hill's equation."""
        # Default curve: x values are normalized velocities, y values are force scaling factors
        # Negative velocity = concentric contraction, positive = eccentric
        v_norm_concentric = np.linspace(-1, 0, 50)
        v_norm_eccentric = np.linspace(0, 1, 50)
        
        # Hill's equation for concentric contraction
        f_concentric = (1 + v_norm_concentric) / (1 - v_norm_concentric/0.25)
        
        # Eccentric contraction (lengthening)
        f_eccentric = 1.8 - 0.8 * (1 + v_norm_eccentric) / (1 + 2 * v_norm_eccentric)
        
        v_norm = np.concatenate((v_norm_concentric, v_norm_eccentric))
        f_norm = np.concatenate((f_concentric, f_eccentric))
        
        return {'x': v_norm.tolist(), 'y': f_norm.tolist()}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert muscle parameters to dictionary."""
        return {
            'name': self.name,
            'optimal_fiber_length': self.optimal_fiber_length,
            'max_isometric_force': self.max_isometric_force,
            'tendon_slack_length': self.tendon_slack_length,
            'pennation_angle': self.pennation_angle,
            'max_contraction_velocity': self.max_contraction_velocity,
            'activation_time_constant': self.activation_time_constant,
            'deactivation_time_constant': self.deactivation_time_constant,
            'force_length_curve': self.force_length_curve,
            'force_velocity_curve': self.force_velocity_curve
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MuscleParameters':
        """Create muscle parameters from dictionary."""
        return cls(
            name=data['name'],
            optimal_fiber_length=data['optimal_fiber_length'],
            max_isometric_force=data['max_isometric_force'],
            tendon_slack_length=data['tendon_slack_length'],
            pennation_angle=data.get('pennation_angle', 0.0),
            max_contraction_velocity=data.get('max_contraction_velocity'),
            activation_time_constant=data.get('activation_time_constant', 0.01),
            deactivation_time_constant=data.get('deactivation_time_constant', 0.04),
            force_length_curve=data.get('force_length_curve'),
            force_velocity_curve=data.get('force_velocity_curve')
        )

def calculate_muscle_force(
    muscle_params: MuscleParameters,
    activation: float,
    fiber_length: float,
    fiber_velocity: float
) -> float:
    """
    Calculate muscle force using a Hill-type muscle model.
    
    Args:
        muscle_params: Parameters of the muscle
        activation: Muscle activation level (0-1)
        fiber_length: Current fiber length in meters
        fiber_velocity: Current fiber contraction velocity in m/s (negative for shortening)
        
    Returns:
        Calculated muscle force in Newtons
    """
    # Normalized fiber length
    norm_length = fiber_length / muscle_params.optimal_fiber_length
    
    # Normalized fiber velocity
    max_velocity = muscle_params.max_contraction_velocity
    norm_velocity = fiber_velocity / max_velocity
    
    # Force-length relationship
    fl_curve = muscle_params.force_length_curve
    fl_x = np.array(fl_curve['x'])
    fl_y = np.array(fl_curve['y'])
    f_length = np.interp(norm_length, fl_x, fl_y)
    
    # Force-velocity relationship
    fv_curve = muscle_params.force_velocity_curve
    fv_x = np.array(fv_curve['x'])
    fv_y = np.array(fv_curve['y'])
    f_velocity = np.interp(norm_velocity, fv_x, fv_y)
    
    # Passive force (simplified model)
    # Increases exponentially when muscle is stretched beyond optimal length
    if norm_length > 1.0:
        passive_force = 0.2 * np.exp(10 * (norm_length - 1.0) - 1)
    else:
        passive_force = 0.0
    
    # Total muscle force
    active_force = activation * f_length * f_velocity * muscle_params.max_isometric_force
    
    # Account for pennation angle
    cos_pennation = np.cos(muscle_params.pennation_angle)
    
    # Total force along tendon
    total_force = (active_force + passive_force * muscle_params.max_isometric_force) * cos_pennation
    
    return total_force

def calculate_muscle_activation(
    excitation: Union[float, np.ndarray],
    current_activation: Union[float, np.ndarray],
    time_step: float,
    activation_time_constant: float = 0.01,
    deactivation_time_constant: float = 0.04
) -> Union[float, np.ndarray]:
    """
    Calculate muscle activation dynamics using a first-order differential equation.
    
    Args:
        excitation: Neural excitation signal (0-1)
        current_activation: Current activation level (0-1)
        time_step: Time step for integration in seconds
        activation_time_constant: Time constant for activation in seconds
        deactivation_time_constant: Time constant for deactivation in seconds
        
    Returns:
        Updated muscle activation level
    """
    # Select the appropriate time constant based on whether activation is increasing or decreasing
    tau = np.where(excitation > current_activation, 
                  activation_time_constant, 
                  deactivation_time_constant)
    
    # First-order differential equation for activation dynamics
    activation_derivative = (excitation - current_activation) / tau
    
    # Integrate using forward Euler method
    new_activation = current_activation + activation_derivative * time_step
    
    # Ensure activation stays within valid range [0, 1]
    new_activation = np.clip(new_activation, 0, 1)
    
    return new_activation

def calculate_muscle_length_and_velocity(
    origin: np.ndarray,
    insertion: np.ndarray,
    previous_length: Optional[float] = None,
    previous_time: Optional[float] = None,
    current_time: Optional[float] = None,
    via_points: Optional[List[np.ndarray]] = None,
    tendon_slack_length: Optional[float] = None
) -> Tuple[float, float, float]:
    """
    Calculate muscle-tendon length and velocity based on attachment points.
    
    Args:
        origin: Origin point coordinates (3D)
        insertion: Insertion point coordinates (3D)
        previous_length: Previous muscle-tendon length for velocity calculation
        previous_time: Time of previous calculation for velocity
        current_time: Current time for velocity calculation
        via_points: List of via points (intermediate points along the muscle path)
        tendon_slack_length: Slack length of the tendon
        
    Returns:
        Tuple of (muscle_tendon_length, fiber_length, fiber_velocity)
    """
    # Calculate muscle path
    if via_points is None or len(via_points) == 0:
        # Straight line from origin to insertion
        muscle_path = [origin, insertion]
        path_vectors = [insertion - origin]
    else:
        # Include via points
        muscle_path = [origin] + via_points + [insertion]
        path_vectors = []
        for i in range(len(muscle_path) - 1):
            path_vectors.append(muscle_path[i+1] - muscle_path[i])
    
    # Calculate total muscle-tendon length
    muscle_tendon_length = sum(np.linalg.norm(vector) for vector in path_vectors)
    
    # Calculate fiber length
    if tendon_slack_length is not None:
        # Simple model: fiber_length = muscle_tendon_length - tendon_slack_length
        fiber_length = max(0.01, muscle_tendon_length - tendon_slack_length)
    else:
        # If tendon slack length is not provided, assume fiber length is 70% of total length
        fiber_length = 0.7 * muscle_tendon_length
    
    # Calculate velocity if previous data is available
    if previous_length is not None and previous_time is not None and current_time is not None:
        time_diff = current_time - previous_time
        if time_diff > 0:
            fiber_velocity = (fiber_length - previous_length) / time_diff
        else:
            fiber_velocity = 0.0
    else:
        fiber_velocity = 0.0
    
    return muscle_tendon_length, fiber_length, fiber_velocity

def estimate_muscle_parameters_from_anatomy(
    origin: np.ndarray,
    insertion: np.ndarray,
    pcsa: float,  # Physiological cross-sectional area in cm^2
    fiber_length_ratio: float = 0.7,  # Ratio of fiber length to muscle-tendon length
    pennation_angle: float = 0.0,  # Pennation angle in radians
    specific_tension: float = SPECIFIC_TENSION,  # N/cm^2
    name: str = "unnamed_muscle"
) -> MuscleParameters:
    """
    Estimate muscle parameters based on anatomical data.
    
    Args:
        origin: Origin point coordinates (3D)
        insertion: Insertion point coordinates (3D)
        pcsa: Physiological cross-sectional area in cm^2
        fiber_length_ratio: Ratio of fiber length to muscle-tendon length
        pennation_angle: Pennation angle in radians
        specific_tension: Specific tension in N/cm^2
        name: Muscle name
        
    Returns:
        MuscleParameters object with estimated parameters
    """
    # Calculate muscle-tendon length
    muscle_tendon_length = np.linalg.norm(insertion - origin)
    
    # Estimate optimal fiber length
    optimal_fiber_length = fiber_length_ratio * muscle_tendon_length
    
    # Estimate tendon slack length
    tendon_slack_length = muscle_tendon_length - optimal_fiber_length * np.cos(pennation_angle)
    
    # Calculate maximum isometric force
    max_isometric_force = pcsa * specific_tension * PENNATION_FACTOR
    
    # Create and return muscle parameters
    return MuscleParameters(
        name=name,
        optimal_fiber_length=optimal_fiber_length,
        max_isometric_force=max_isometric_force,
        tendon_slack_length=tendon_slack_length,
        pennation_angle=pennation_angle
    )

def define_standard_muscles() -> Dict[str, MuscleParameters]:
    """
    Define a set of standard muscles with typical parameters.
    
    Returns:
        Dictionary mapping muscle names to MuscleParameters
    """
    muscles = {}
    
    # Lower extremity muscles
    muscles['gluteus_maximus'] = MuscleParameters(
        name="Gluteus Maximus",
        optimal_fiber_length=0.142,
        max_isometric_force=1944,
        tendon_slack_length=0.125,
        pennation_angle=0.087  # ~5 degrees
    )
    
    muscles['gluteus_medius'] = MuscleParameters(
        name="Gluteus Medius",
        optimal_fiber_length=0.054,
        max_isometric_force=1119,
        tendon_slack_length=0.078,
        pennation_angle=0.0
    )
    
    muscles['iliopsoas'] = MuscleParameters(
        name="Iliopsoas",
        optimal_fiber_length=0.1,
        max_isometric_force=1535,
        tendon_slack_length=0.13,
        pennation_angle=0.0
    )
    
    muscles['rectus_femoris'] = MuscleParameters(
        name="Rectus Femoris",
        optimal_fiber_length=0.075,
        max_isometric_force=1169,
        tendon_slack_length=0.346,
        pennation_angle=0.087  # ~5 degrees
    )
    
    muscles['vastus_lateralis'] = MuscleParameters(
        name="Vastus Lateralis",
        optimal_fiber_length=0.084,
        max_isometric_force=1871,
        tendon_slack_length=0.157,
        pennation_angle=0.052  # ~3 degrees
    )
    
    muscles['vastus_medialis'] = MuscleParameters(
        name="Vastus Medialis",
        optimal_fiber_length=0.089,
        max_isometric_force=1294,
        tendon_slack_length=0.126,
        pennation_angle=0.052  # ~3 degrees
    )
    
    muscles['hamstrings'] = MuscleParameters(
        name="Hamstrings",
        optimal_fiber_length=0.109,
        max_isometric_force=1880,
        tendon_slack_length=0.31,
        pennation_angle=0.087  # ~5 degrees
    )
    
    muscles['gastrocnemius'] = MuscleParameters(
        name="Gastrocnemius",
        optimal_fiber_length=0.055,
        max_isometric_force=1606,
        tendon_slack_length=0.39,
        pennation_angle=0.17  # ~10 degrees
    )
    
    muscles['soleus'] = MuscleParameters(
        name="Soleus",
        optimal_fiber_length=0.03,
        max_isometric_force=3549,
        tendon_slack_length=0.25,
        pennation_angle=0.45  # ~25 degrees
    )
    
    muscles['tibialis_anterior'] = MuscleParameters(
        name="Tibialis Anterior",
        optimal_fiber_length=0.082,
        max_isometric_force=905,
        tendon_slack_length=0.31,
        pennation_angle=0.087  # ~5 degrees
    )
    
    # Upper extremity muscles
    muscles['deltoid'] = MuscleParameters(
        name="Deltoid",
        optimal_fiber_length=0.097,
        max_isometric_force=1142,
        tendon_slack_length=0.04,
        pennation_angle=0.15  # ~9 degrees
    )
    
    muscles['biceps_brachii'] = MuscleParameters(
        name="Biceps Brachii",
        optimal_fiber_length=0.116,
        max_isometric_force=414,
        tendon_slack_length=0.2723,
        pennation_angle=0.0
    )
    
    muscles['triceps_brachii'] = MuscleParameters(
        name="Triceps Brachii",
        optimal_fiber_length=0.084,
        max_isometric_force=798,
        tendon_slack_length=0.1,
        pennation_angle=0.1  # ~6 degrees
    )
    
    return muscles

def calculate_moment_arm(
    muscle_path: List[np.ndarray],
    joint_center: np.ndarray,
    joint_axis: np.ndarray
) -> float:
    """
    Calculate the moment arm of a muscle with respect to a joint.
    
    Args:
        muscle_path: List of points defining the muscle path
        joint_center: Coordinates of the joint center
        joint_axis: Unit vector defining the joint's axis of rotation
        
    Returns:
        Moment arm in meters
    """
    # Normalize the joint axis
    joint_axis = joint_axis / np.linalg.norm(joint_axis)
    
    # Calculate the moment arm for each segment of the muscle path
    moment_arms = []
    
    for i in range(len(muscle_path) - 1):
        p1 = muscle_path[i]
        p2 = muscle_path[i+1]
        
        # Vector from joint center to segment start
        r1 = p1 - joint_center
        
        # Vector from joint center to segment end
        r2 = p2 - joint_center
        
        # Muscle segment vector
        segment = p2 - p1
        segment_length = np.linalg.norm(segment)
        
        if segment_length < 1e-10:
            continue
            
        # Normalize segment vector
        segment_unit = segment / segment_length
        
        # Calculate perpendicular distance from joint axis to muscle line
        # by taking the cross product of the position vector and segment direction
        cross1 = np.cross(r1, segment_unit)
        cross2 = np.cross(r2, segment_unit)
        
        # Project onto the joint axis to get the moment arm
        ma1 = np.dot(cross1, joint_axis)
        ma2 = np.dot(cross2, joint_axis)
        
        # Take average moment arm for this segment
        moment_arms.append((ma1 + ma2) / 2)
    
    # Return the weighted average moment arm across all segments
    if moment_arms:
        return sum(moment_arms) / len(moment_arms)
    else:
        return 0.0

def simulate_muscle_activation(
    neural_excitation: List[float],
    time_points: List[float],
    activation_time_constant: float = 0.01,
    deactivation_time_constant: float = 0.04,
    initial_activation: float = 0.0
) -> List[float]:
    """
    Simulate muscle activation response to neural excitation over time.
    
    Args:
        neural_excitation: List of neural excitation values over time
        time_points: Corresponding time points in seconds
        activation_time_constant: Time constant for activation in seconds
        deactivation_time_constant: Time constant for deactivation in seconds
        initial_activation: Initial activation level
        
    Returns:
        List of activation values corresponding to each time point
    """
    # Ensure input arrays are the same length
    if len(neural_excitation) != len(time_points):
        raise ValueError("neural_excitation and time_points must have the same length")
    
    # Initialize activation array
    activation = [initial_activation]
    
    # Simulate activation dynamics for each time step
    for i in range(1, len(time_points)):
        # Calculate time step
        dt = time_points[i] - time_points[i-1]
        
        # Get current excitation
        excitation = neural_excitation[i]
        
        # Update activation using the activation dynamics model
        new_activation = calculate_muscle_activation(
            excitation,
            activation[-1],
            dt,
            activation_time_constant,
            deactivation_time_constant
        )
        
        activation.append(new_activation)
    
    return activation

def optimize_muscle_excitations(
    target_joint_moments: Dict[str, List[float]],
    time_points: List[float],
    muscles: Dict[str, MuscleParameters],
    muscle_paths: Dict[str, List[np.ndarray]],
    joint_centers: Dict[str, np.ndarray],
    joint_axes: Dict[str, np.ndarray],
    muscle_to_joint_map: Dict[str, List[str]],
    max_iterations: int = 100
) -> Dict[str, List[float]]:
    """
    Optimize muscle excitations to produce desired joint moments.
    
    Args:
        target_joint_moments: Dictionary mapping joint names to target moment time series
        time_points: Time points for the simulation
        muscles: Dictionary of muscle parameters
        muscle_paths: Dictionary mapping muscle names to muscle paths
        joint_centers: Dictionary mapping joint names to joint centers
        joint_axes: Dictionary mapping joint names to joint rotation axes
        muscle_to_joint_map: Dictionary mapping muscle names to list of joints they affect
        max_iterations: Maximum number of optimization iterations
        
    Returns:
        Dictionary mapping muscle names to optimized excitation patterns
    """
    # Get list of all muscles and joints
    all_muscles = list(muscles.keys())
    all_joints = list(target_joint_moments.keys())
    
    # Calculate moment arms for each muscle-joint pair
    moment_arms = {}
    for muscle_name, muscle_path in muscle_paths.items():
        moment_arms[muscle_name] = {}
        for joint_name in muscle_to_joint_map.get(muscle_name, []):
            if joint_name not in joint_centers or joint_name not in joint_axes:
                continue
                
            moment_arms[muscle_name][joint_name] = calculate_moment_arm(
                muscle_path,
                joint_centers[joint_name],
                joint_axes[joint_name]
            )
    
    # Define the objective function for optimization
    def objective_function(x):
        # Reshape excitations: rows are muscles, columns are time points
        excitations = x.reshape(len(all_muscles), len(time_points))
        
        # Calculate activation for each muscle
        activations = {}
        for i, muscle_name in enumerate(all_muscles):
            activations[muscle_name] = simulate_muscle_activation(
                excitations[i].tolist(),
                time_points,
                muscles[muscle_name].activation_time_constant,
                muscles[muscle_name].deactivation_time_constant
            )
        
        # Calculate joint moments produced by muscles
        produced_moments = {joint_name: np.zeros(len(time_points)) for joint_name in all_joints}
        
        for muscle_name in all_muscles:
            for joint_name in muscle_to_joint_map.get(muscle_name, []):
                if joint_name not in moment_arms[muscle_name]:
                    continue
                    
                # Get moment arm
                ma = moment_arms[muscle_name][joint_name]
                
                # Calculate muscle force at each time point (simplified)
                # Here we assume a constant muscle length and velocity
                muscle_forces = [
                    calculate_muscle_force(
                        muscles[muscle_name],
                        act,
                        muscles[muscle_name].optimal_fiber_length,
                        0.0  # Assuming isometric contraction
                    )
                    for act in activations[muscle_name]
                ]
                
                # Calculate moments
                moments = np.array(muscle_forces) * ma
                
                # Add to produced moments
                produced_moments[joint_name] += moments
        
        # Calculate error between produced and target moments
        error = 0.0
        for joint_name in all_joints:
            if joint_name in target_joint_moments:
                target = np.array(target_joint_moments[joint_name])
                produced = produced_moments[joint_name]
                
                # Mean squared error
                joint_error = np.mean((target - produced) ** 2)
                error += joint_error
        
        # Add regularization to minimize activation
        activation_penalty = 0.01 * np.sum(x ** 2)
        
        # Add penalty for rapid changes in activation
        smoothness_penalty = 0.0
        for i, muscle_name in enumerate(all_muscles):
            muscle_excitation = excitations[i]
            d_excitation = np.diff(muscle_excitation)
            smoothness_penalty += 0.01 * np.sum(d_excitation ** 2)
        
        return error + activation_penalty + smoothness_penalty
    
    # Set up optimization bounds (0 to 1 for all excitations)
    bounds = [(0, 1) for _ in range(len(all_muscles) * len(time_points))]
    
    # Initial guess: minimal excitation for all muscles
    initial_guess = np.ones(len(all_muscles) * len(time_points)) * 0.1
    
    # Run optimization
    result = optimize.minimize(
        objective_function,
        initial_guess,
        bounds=bounds,
        method='L-BFGS-B',
        options={'maxiter': max_iterations}
    )
    
    # Extract optimized excitations
    optimized_excitations = result.x.reshape(len(all_muscles), len(time_points))
    
    # Return as dictionary
    excitation_dict = {}
    for i, muscle_name in enumerate(all_muscles):
        excitation_dict[muscle_name] = optimized_excitations[i].tolist()
    
    return excitation_dict

def load_muscle_data(filepath: str) -> Dict[str, MuscleParameters]:
    """
    Load muscle data from a JSON file.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        Dictionary mapping muscle names to MuscleParameters
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        muscles = {}
        for muscle_name, muscle_data in data.items():
            muscles[muscle_name] = MuscleParameters.from_dict(muscle_data)
            
        return muscles
    except Exception as e:
        print(f"Error loading muscle data from {filepath}: {str(e)}")
        return {}

def save_muscle_data(muscles: Dict[str, MuscleParameters], filepath: str) -> bool:
    """
    Save muscle data to a JSON file.
    
    Args:
        muscles: Dictionary mapping muscle names to MuscleParameters
        filepath: Output file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        data = {name: muscle.to_dict() for name, muscle in muscles.items()}
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
            
        return True
    except Exception as e:
        print(f"Error saving muscle data to {filepath}: {str(e)}")
        return False 