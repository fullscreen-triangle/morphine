"""
Biomechanical Core (biomech_core)
---------------------------------
A Python package for biomechanical analysis and calculations.

This package extracts and refines the best functionalities from the BMC-master
notebooks into a cohesive API for analyzing human movements, calculating body 
segment parameters, and optimizing biomechanical models.

Primary modules:
    - segments: Body segment parameter calculations and inertial properties
    - kinematics: Motion analysis including joint angles, velocities, and accelerations
    - kinetics: Force, moment, and energy calculations
    - muscle: Muscle dynamics, activation, and force-length-velocity relationships
    - stability: Postural control, balance, and stabilography
    - gait: Specialized analysis for walking and running
    - optimization: Tools for finding optimal postures and trajectories

The package is designed to integrate with the orchestration solver for enhancing
biomechanical queries with AI assistants.
"""

__version__ = '0.1.0'

from . import segments
from . import kinematics
from . import kinetics
from . import muscle
from . import stability
from . import gait
from . import optimization
from . import utils

# Convenience imports for commonly used functions
from .segments import (
    calculate_body_segment_parameters,
    calculate_center_of_mass,
    calculate_moment_of_inertia
)

from .kinematics import (
    calculate_joint_angles,
    calculate_angular_velocity,
    calculate_linear_velocity,
    calculate_acceleration
)

from .kinetics import (
    calculate_joint_forces,
    calculate_joint_moments,
    calculate_power,
    calculate_work,
    calculate_energy
)

from .muscle import (
    calculate_muscle_force,
    calculate_muscle_activation,
    calculate_muscle_length_and_velocity,
    MuscleParameters
)

from .stability import (
    calculate_cop_from_force_plate,
    calculate_stability_metrics,
    calculate_limits_of_stability,
    romberg_quotient
)

from .gait import (
    analyze_gait_cycle,
    calculate_stride_parameters,
    identify_gait_events
)

from .optimization import (
    minimum_jerk_trajectory,
    principle_of_least_action_trajectory,
    optimize_posture,
    minimize_joint_loads,
    maximize_performance
) 