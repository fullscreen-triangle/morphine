import logging
import json
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

class QueryProcessor:
    """
    Query processor that translates user input and GLB model interactions
    into a structured optimization problem.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the query processor.
        
        Args:
            config: Configuration dictionary with processing parameters
        """
        self.config = config
        self.embedding_model = config.get("embedding_model", "biomechanical_embeddings")
        self.knowledge_base_path = Path(config.get("knowledge_base_path", "data/knowledge_base"))
        self.context_window = config.get("context_window", 5)  # Temporal context window
        
        # Load biomechanical knowledge and constraints
        self.joint_limits = self._load_joint_limits()
        self.movement_patterns = self._load_movement_patterns()
        
        logger.info("Query processor initialized")
    
    def process_user_input(self, 
                         text_query: str, 
                         glb_interaction: Dict[str, Any], 
                         user_constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process user input and GLB model interactions into a structured query.
        
        Args:
            text_query: Natural language query from the user
            glb_interaction: Data from user's interaction with the GLB model
            user_constraints: Additional constraints specified by the user
            
        Returns:
            Structured query for the optimizer/LLM
        """
        logger.info(f"Processing user input: {text_query[:100]}...")
        
        # Extract parameters from GLB interaction
        model_params = self._extract_model_parameters(glb_interaction)
        
        # Extract movement phases if present
        movement_phases = self._extract_movement_phases(glb_interaction)
        
        # Extract biomechanical intent from text query
        intent = self._extract_intent(text_query)
        
        # Formulate constraints from user input and biomechanical knowledge
        constraints = self._formulate_constraints(model_params, user_constraints)
        
        # Create optimization targets based on intent and parameters
        optimization_targets = self._create_optimization_targets(intent, model_params, movement_phases)
        
        # Translate everything into a structured query format
        structured_query = {
            "text": text_query,
            "model_params": model_params,
            "intent": intent,
            "constraints": constraints,
            "optimization_targets": optimization_targets,
            "movement_phases": movement_phases,
            "reference_data": self._find_reference_data(intent, model_params)
        }
        
        return structured_query
    
    def _extract_model_parameters(self, glb_interaction: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract relevant biomechanical parameters from GLB interaction.
        
        Args:
            glb_interaction: User's interaction with the GLB model
            
        Returns:
            Dictionary of model parameters
        """
        # Extract joint angles, positions, etc. from GLB interaction
        joint_params = {}
        
        # Process different interaction types
        if "pose_data" in glb_interaction:
            # User has manipulated specific joints/pose
            pose_data = glb_interaction["pose_data"]
            
            for joint_name, joint_data in pose_data.items():
                if "rotation" in joint_data:
                    # Convert to anatomical angles if needed
                    joint_params[f"{joint_name}_x_rotation"] = joint_data["rotation"].get("x", 0)
                    joint_params[f"{joint_name}_y_rotation"] = joint_data["rotation"].get("y", 0)
                    joint_params[f"{joint_name}_z_rotation"] = joint_data["rotation"].get("z", 0)
                
                if "position" in joint_data:
                    joint_params[f"{joint_name}_x_position"] = joint_data["position"].get("x", 0)
                    joint_params[f"{joint_name}_y_position"] = joint_data["position"].get("y", 0)
                    joint_params[f"{joint_name}_z_position"] = joint_data["position"].get("z", 0)
        
        if "global_params" in glb_interaction:
            # Global model parameters
            for param_name, param_value in glb_interaction["global_params"].items():
                joint_params[param_name] = param_value
        
        # Calculate derived parameters (e.g., knee flexion from rotations)
        derived_params = self._calculate_derived_parameters(joint_params)
        joint_params.update(derived_params)
        
        return joint_params
    
    def _calculate_derived_parameters(self, params: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate derived biomechanical parameters from raw model parameters.
        
        Args:
            params: Raw model parameters
            
        Returns:
            Dictionary of derived parameters
        """
        derived = {}
        
        # Example: Calculate knee flexion angle from rotations
        if "knee_r_y_rotation" in params and "hip_r_y_rotation" in params:
            # Simplified calculation for knee flexion (would be more complex in real implementation)
            derived["knee_flexion_angle"] = abs(params["knee_r_y_rotation"])
        
        # Example: Calculate shoulder abduction
        if "shoulder_r_z_rotation" in params:
            derived["shoulder_abduction"] = abs(params["shoulder_r_z_rotation"])
        
        return derived
    
    def _extract_movement_phases(self, glb_interaction: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Extract movement phases if present in the GLB interaction.
        
        Args:
            glb_interaction: User's interaction with the GLB model
            
        Returns:
            List of movement phases or None
        """
        if "movement_timeline" in glb_interaction:
            timeline = glb_interaction["movement_timeline"]
            
            # Process timeline into discrete phases
            phases = []
            current_phase = {}
            
            for frame in timeline:
                # Determine if this is a new phase based on velocity changes or user markers
                is_new_phase = frame.get("is_key_frame", False)
                
                if is_new_phase and current_phase:
                    phases.append(current_phase)
                    current_phase = {}
                
                # Add frame data to current phase
                if "frame_id" not in current_phase:
                    current_phase = {
                        "start_frame": frame["frame_id"],
                        "params": frame["params"],
                        "frames": [frame]
                    }
                else:
                    current_phase["end_frame"] = frame["frame_id"]
                    current_phase["frames"].append(frame)
            
            # Add the last phase if it exists
            if current_phase:
                phases.append(current_phase)
                
            return phases
        
        return None
    
    def _extract_intent(self, text_query: str) -> Dict[str, Any]:
        """
        Extract biomechanical intent from the text query.
        
        Args:
            text_query: Natural language query from the user
            
        Returns:
            Dictionary with intent information
        """
        # This would ideally use an NLP model to extract intent
        # Here is a simplified rule-based approach
        intent = {
            "primary_goal": "",
            "secondary_goals": [],
            "focus_areas": [],
            "optimization_type": "performance"  # or "injury_prevention", "efficiency", etc.
        }
        
        # Extract primary goal
        if "improve" in text_query.lower():
            intent["primary_goal"] = "improvement"
        elif "optimize" in text_query.lower():
            intent["primary_goal"] = "optimization"
        elif "correct" in text_query.lower():
            intent["primary_goal"] = "correction"
        else:
            intent["primary_goal"] = "analysis"
        
        # Extract focus areas
        body_parts = ["knee", "hip", "ankle", "shoulder", "elbow", "spine", "neck", "wrist"]
        intent["focus_areas"] = [part for part in body_parts if part in text_query.lower()]
        
        # Determine optimization type
        if any(term in text_query.lower() for term in ["injur", "pain", "discomfort", "safe"]):
            intent["optimization_type"] = "injury_prevention"
        elif any(term in text_query.lower() for term in ["perform", "power", "strength", "speed"]):
            intent["optimization_type"] = "performance"
        elif any(term in text_query.lower() for term in ["efficien", "energy", "econom"]):
            intent["optimization_type"] = "efficiency"
        
        return intent
    
    def _formulate_constraints(self, 
                             model_params: Dict[str, float],
                             user_constraints: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Formulate biomechanical constraints for the optimization problem.
        
        Args:
            model_params: Current model parameters
            user_constraints: Additional constraints specified by the user
            
        Returns:
            List of constraints for the optimizer
        """
        constraints = []
        
        # Add anatomical constraints (joint limits)
        for joint, limits in self.joint_limits.items():
            if joint in model_params:
                constraints.append({
                    "type": "bound",
                    "parameter": joint,
                    "min": limits.get("min", 0),
                    "max": limits.get("max", 0),
                    "priority": "high",  # Anatomical constraints are high priority
                    "description": f"Anatomical limit for {joint}"
                })
        
        # Add biomechanical relationship constraints
        # Example: knee and hip flexion relationship during squat
        if "knee_flexion_angle" in model_params and "hip_flexion_angle" in model_params:
            constraints.append({
                "type": "relationship",
                "expression": "knee_flexion_angle > 0.7 * hip_flexion_angle",
                "priority": "medium",
                "description": "Maintain appropriate knee-hip flexion ratio"
            })
        
        # Add user-specified constraints
        if user_constraints:
            for constraint_name, constraint_data in user_constraints.items():
                constraints.append({
                    "type": constraint_data.get("type", "custom"),
                    "parameter": constraint_data.get("parameter", ""),
                    "value": constraint_data.get("value", 0),
                    "expression": constraint_data.get("expression", ""),
                    "priority": "high",  # User constraints are high priority
                    "description": f"User constraint: {constraint_name}"
                })
        
        return constraints
    
    def _create_optimization_targets(self, 
                                  intent: Dict[str, Any],
                                  model_params: Dict[str, float],
                                  movement_phases: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Create optimization targets based on intent and parameters.
        
        Args:
            intent: Extracted user intent
            model_params: Current model parameters
            movement_phases: Movement phases if available
            
        Returns:
            Optimization targets for the solver
        """
        optimization_targets = {
            "objective_function": "",
            "target_parameters": {},
            "weights": {},
            "multi_phase": movement_phases is not None
        }
        
        # Set objective function based on intent
        if intent["optimization_type"] == "injury_prevention":
            optimization_targets["objective_function"] = "minimize_joint_stress"
            
            # Set weights higher for focus areas
            for area in intent["focus_areas"]:
                related_params = [param for param in model_params if area in param]
                for param in related_params:
                    optimization_targets["weights"][param] = 2.0  # Higher weight
            
        elif intent["optimization_type"] == "performance":
            optimization_targets["objective_function"] = "maximize_power_output"
            
            # Set target parameters for performance
            if "knee" in intent["focus_areas"]:
                optimization_targets["target_parameters"]["knee_flexion_angle"] = 110.0  # Optimal for power
                
            if "hip" in intent["focus_areas"]:
                optimization_targets["target_parameters"]["hip_flexion_angle"] = 120.0  # Optimal for power
                
        elif intent["optimization_type"] == "efficiency":
            optimization_targets["objective_function"] = "minimize_energy_expenditure"
            
            # Set weights for efficiency
            optimization_targets["weights"] = {
                "joint_velocity": 0.7,
                "joint_acceleration": 1.0,
                "balance_stability": 0.8
            }
        
        # Handle multi-phase optimization if phases are available
        if movement_phases:
            optimization_targets["phase_targets"] = []
            
            for i, phase in enumerate(movement_phases):
                phase_target = {
                    "phase_index": i,
                    "start_frame": phase.get("start_frame", 0),
                    "end_frame": phase.get("end_frame", 0),
                    "objective_function": optimization_targets["objective_function"],
                    "weights": dict(optimization_targets["weights"])  # Copy base weights
                }
                
                # Adjust weights based on phase (e.g., landing phase needs more injury prevention)
                if i == len(movement_phases) - 1 and "landing" in str(phase).lower():
                    phase_target["weights"] = {k: v * 1.5 for k, v in phase_target["weights"].items()}
                    
                optimization_targets["phase_targets"].append(phase_target)
        
        return optimization_targets
    
    def _find_reference_data(self, intent: Dict[str, Any], model_params: Dict[str, float]) -> Dict[str, Any]:
        """
        Find reference biomechanical data for comparison.
        
        Args:
            intent: User intent
            model_params: Current model parameters
            
        Returns:
            Reference data for comparison
        """
        reference_data = {}
        
        # This would typically query a database of expert movements
        # For now, we'll use simplified example data
        
        # Find pattern matches in the movement database
        if intent["focus_areas"] and intent["primary_goal"]:
            focus = intent["focus_areas"][0] if intent["focus_areas"] else "general"
            
            if focus in self.movement_patterns:
                reference_data["expert_pattern"] = self.movement_patterns[focus]
        
        # Add normative data
        if "knee_flexion_angle" in model_params:
            reference_data["normative_ranges"] = {
                "knee_flexion_angle": {
                    "athletic": (100, 140),
                    "normal": (90, 130),
                    "limited": (70, 100)
                }
            }
        
        return reference_data
    
    def _load_joint_limits(self) -> Dict[str, Dict[str, float]]:
        """
        Load anatomical joint limits from knowledge base.
        
        Returns:
            Dictionary of joint limits
        """
        # This would load from a file in a real implementation
        # Example joint limits
        return {
            "knee_flexion_angle": {"min": 0, "max": 160},
            "hip_flexion_angle": {"min": 0, "max": 140},
            "ankle_dorsiflexion": {"min": -20, "max": 30},
            "shoulder_abduction": {"min": 0, "max": 180},
            "elbow_flexion": {"min": 0, "max": 160},
            "spine_flexion": {"min": -30, "max": 90}
        }
    
    def _load_movement_patterns(self) -> Dict[str, Any]:
        """
        Load expert movement patterns from knowledge base.
        
        Returns:
            Dictionary of movement patterns
        """
        # This would load from a file in a real implementation
        # Example movement patterns
        return {
            "knee": {
                "squat": {
                    "phases": ["descent", "bottom", "ascent"],
                    "key_parameters": ["knee_flexion_angle", "hip_flexion_angle", "ankle_dorsiflexion"],
                    "optimal_values": {
                        "knee_flexion_angle": 120,
                        "hip_flexion_angle": 110,
                        "ankle_dorsiflexion": 25
                    }
                },
                "jump": {
                    "phases": ["preparation", "takeoff", "flight", "landing"],
                    "key_parameters": ["knee_flexion_angle", "hip_flexion_angle", "ankle_plantar_flexion"],
                    "optimal_values": {
                        "knee_flexion_angle": 130,
                        "hip_flexion_angle": 120,
                        "ankle_plantar_flexion": 40
                    }
                }
            },
            "shoulder": {
                "throw": {
                    "phases": ["wind-up", "cocking", "acceleration", "follow-through"],
                    "key_parameters": ["shoulder_external_rotation", "elbow_flexion", "trunk_rotation"],
                    "optimal_values": {
                        "shoulder_external_rotation": 170,
                        "elbow_flexion": 90,
                        "trunk_rotation": 60
                    }
                }
            }
        } 