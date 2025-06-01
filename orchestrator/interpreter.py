import logging
import json
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

class GlbInterpreter:
    """
    Interpreter that translates optimized biomechanical parameters
    back into the GLB model format for visualization.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the GLB interpreter.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.mapping_cache = {}
        self.skeleton_template = self._load_skeleton_template()
        self.animation_templates = self._load_animation_templates()
        
        logger.info("GLB interpreter initialized")
    
    def interpret(self, solution: Dict[str, Any], query_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interpret the optimized solution and translate it to GLB model parameters.
        
        Args:
            solution: Optimized solution from the solver
            query_context: Original query context including GLB model state
            
        Returns:
            GLB model updates to be applied to the frontend
        """
        logger.info("Interpreting solution to GLB model parameters...")
        
        # Extract solution parameters
        optimized_params = solution.get("optimized_params", {})
        original_params = solution.get("original_params", {})
        
        # Determine if this is a static pose or animation
        is_animation = "movement_phases" in query_context
        
        if is_animation:
            # Generate animation keyframes
            glb_updates = self._interpret_animation(optimized_params, query_context)
        else:
            # Generate static pose
            glb_updates = self._interpret_static_pose(optimized_params, query_context)
        
        # Add metadata to the updates
        glb_updates["meta"] = {
            "interpretation_type": "animation" if is_animation else "static_pose",
            "solution_confidence": solution.get("confidence", 0.8),
            "significant_changes": self._identify_significant_changes(optimized_params, original_params)
        }
        
        return glb_updates
    
    def _interpret_static_pose(self, optimized_params: Dict[str, float], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interpret optimized parameters as a static pose for the GLB model.
        
        Args:
            optimized_params: Optimized biomechanical parameters
            context: Query context with original GLB model state
            
        Returns:
            GLB model updates for static pose
        """
        # Get original GLB model state
        original_glb = context.get("glb_interaction", {}).get("pose_data", {})
        
        # Create updates structure
        updates = {
            "type": "static_pose",
            "pose_data": {},
            "global_params": {}
        }
        
        # Map biomechanical parameters to GLB joint rotations and positions
        for param, value in optimized_params.items():
            # Map anatomical parameters to GLB model parameters
            glb_mappings = self._map_param_to_glb(param, value, context)
            
            for glb_param in glb_mappings:
                joint_name = glb_param.get("joint")
                param_type = glb_param.get("type")
                param_value = glb_param.get("value")
                axis = glb_param.get("axis")
                
                if joint_name and param_type and axis and param_value is not None:
                    # Initialize joint if not already in updates
                    if joint_name not in updates["pose_data"]:
                        updates["pose_data"][joint_name] = {}
                    
                    # Initialize parameter type if not already in joint
                    if param_type not in updates["pose_data"][joint_name]:
                        updates["pose_data"][joint_name][param_type] = {}
                    
                    # Set parameter value
                    updates["pose_data"][joint_name][param_type][axis] = param_value
                    
                elif not joint_name and glb_param.get("global_param"):
                    # Handle global parameters (not joint-specific)
                    global_param = glb_param.get("global_param")
                    updates["global_params"][global_param] = param_value
        
        return updates
    
    def _interpret_animation(self, optimized_params: Dict[str, float], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interpret optimized parameters as an animation sequence for the GLB model.
        
        Args:
            optimized_params: Optimized biomechanical parameters
            context: Query context with original GLB model state
            
        Returns:
            GLB model updates for animation
        """
        # Get movement phases from context
        movement_phases = context.get("movement_phases", [])
        
        # Create animation structure
        animation = {
            "type": "animation",
            "duration": len(movement_phases) * 1.0,  # 1 second per phase by default
            "keyframes": [],
            "transitions": []
        }
        
        # Generate keyframes for each phase
        time_offset = 0.0
        for i, phase in enumerate(movement_phases):
            # Calculate phase duration based on complexity
            phase_duration = 1.0  # Default 1 second per phase
            if phase.get("params", {}).get("duration"):
                phase_duration = phase["params"]["duration"]
            
            # Generate keyframe at start of phase
            start_keyframe = self._generate_keyframe_for_phase(
                optimized_params, phase, "start", time_offset
            )
            animation["keyframes"].append(start_keyframe)
            
            # Add mid-phase keyframes if needed
            if len(phase.get("frames", [])) > 2:
                mid_keyframe = self._generate_keyframe_for_phase(
                    optimized_params, phase, "mid", time_offset + phase_duration / 2
                )
                animation["keyframes"].append(mid_keyframe)
            
            # Generate keyframe at end of phase
            end_keyframe = self._generate_keyframe_for_phase(
                optimized_params, phase, "end", time_offset + phase_duration
            )
            animation["keyframes"].append(end_keyframe)
            
            # Add transition between phases
            if i < len(movement_phases) - 1:
                transition = {
                    "from_phase": i,
                    "to_phase": i + 1,
                    "start_time": time_offset + phase_duration,
                    "duration": 0.2,  # Quick transition between phases
                    "easing": "ease-in-out"
                }
                animation["transitions"].append(transition)
            
            # Update time offset for next phase
            time_offset += phase_duration
        
        # Set total animation duration
        animation["duration"] = time_offset
        
        return animation
    
    def _generate_keyframe_for_phase(self, 
                                   optimized_params: Dict[str, float], 
                                   phase: Dict[str, Any],
                                   position: str,  # "start", "mid", or "end"
                                   time: float) -> Dict[str, Any]:
        """
        Generate a keyframe for a specific position in a movement phase.
        
        Args:
            optimized_params: Optimized biomechanical parameters
            phase: Movement phase data
            position: Position in the phase ("start", "mid", or "end")
            time: Timestamp for the keyframe
            
        Returns:
            Keyframe data
        """
        # Initialize keyframe
        keyframe = {
            "time": time,
            "joints": {},
            "phase_position": position,
            "phase_index": phase.get("phase_index", 0)
        }
        
        # Phase-specific parameter modifications
        phase_params = optimized_params.copy()
        
        # Adjust parameters based on phase and position
        phase_name = str(phase.get("name", "")).lower()
        
        if "squat" in phase_name:
            if position == "start" or position == "end":
                # Starting/ending position has less knee/hip flexion
                for joint in ["knee_flexion_angle", "hip_flexion_angle"]:
                    if joint in phase_params:
                        phase_params[joint] *= 0.3  # Reduce flexion at start/end
            elif position == "mid":
                # Mid-squat has maximum knee/hip flexion
                for joint in ["knee_flexion_angle", "hip_flexion_angle"]:
                    if joint in phase_params:
                        phase_params[joint] *= 1.1  # Increase flexion at bottom
        
        elif "jump" in phase_name:
            if position == "start":  # Preparation
                # Preparation has moderate knee/hip flexion
                for joint in ["knee_flexion_angle", "hip_flexion_angle"]:
                    if joint in phase_params:
                        phase_params[joint] *= 0.8
            elif position == "mid" and "flight" in str(phase):  # In flight
                # Flight phase has extension
                for joint in ["knee_flexion_angle", "hip_flexion_angle"]:
                    if joint in phase_params:
                        phase_params[joint] *= 0.2  # Nearly straight
                # Ankle plantar flexion increases for jump
                if "ankle_plantar_flexion" in phase_params:
                    phase_params["ankle_plantar_flexion"] *= 1.5
        
        # Map the adjusted parameters to GLB format
        for param, value in phase_params.items():
            glb_mappings = self._map_param_to_glb(param, value, {"phase": phase})
            
            for glb_param in glb_mappings:
                joint_name = glb_param.get("joint")
                param_type = glb_param.get("type")
                param_value = glb_param.get("value")
                axis = glb_param.get("axis")
                
                if joint_name and param_type and axis:
                    # Initialize joint if needed
                    if joint_name not in keyframe["joints"]:
                        keyframe["joints"][joint_name] = {}
                    
                    # Initialize parameter type if needed
                    if param_type not in keyframe["joints"][joint_name]:
                        keyframe["joints"][joint_name][param_type] = {}
                    
                    # Set parameter value
                    keyframe["joints"][joint_name][param_type][axis] = param_value
        
        return keyframe
    
    def _map_param_to_glb(self, param: str, value: float, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map a biomechanical parameter to GLB model parameters.
        
        Args:
            param: Biomechanical parameter name
            value: Parameter value
            context: Context information
            
        Returns:
            List of GLB parameter mappings
        """
        # Check cache first
        cache_key = f"{param}_{value}"
        if cache_key in self.mapping_cache:
            return self.mapping_cache[cache_key]
        
        # Initialize mapping list
        mappings = []
        
        # Handle different parameter types
        if "knee_flexion_angle" in param:
            # Map knee flexion angle to knee joint rotation
            # Assuming Y-axis rotation for knee flexion in GLB model
            side = "l" if "_l_" in param or "left" in param else "r"
            mappings.append({
                "joint": f"knee_{side}",
                "type": "rotation",
                "axis": "y",
                "value": -value  # Negative because of GLB coordinate system
            })
            
        elif "hip_flexion_angle" in param:
            # Map hip flexion angle to hip joint rotation
            side = "l" if "_l_" in param or "left" in param else "r"
            mappings.append({
                "joint": f"hip_{side}",
                "type": "rotation",
                "axis": "x",
                "value": value
            })
            
        elif "ankle_dorsiflexion" in param:
            # Map ankle dorsiflexion to ankle joint rotation
            side = "l" if "_l_" in param or "left" in param else "r"
            mappings.append({
                "joint": f"ankle_{side}",
                "type": "rotation",
                "axis": "x",
                "value": value
            })
            
        elif "shoulder_abduction" in param:
            # Map shoulder abduction to shoulder joint rotation
            side = "l" if "_l_" in param or "left" in param else "r"
            mappings.append({
                "joint": f"shoulder_{side}",
                "type": "rotation",
                "axis": "z",
                "value": value
            })
            
        elif "elbow_flexion" in param:
            # Map elbow flexion to elbow joint rotation
            side = "l" if "_l_" in param or "left" in param else "r"
            mappings.append({
                "joint": f"elbow_{side}",
                "type": "rotation",
                "axis": "y",
                "value": -value  # Negative because of GLB coordinate system
            })
            
        elif "spine_flexion" in param:
            # Map spine flexion to multiple spine joints
            # Distribute across spine segments
            mappings.append({
                "joint": "spine_01",
                "type": "rotation",
                "axis": "x",
                "value": value * 0.3  # 30% of movement in lower spine
            })
            mappings.append({
                "joint": "spine_02",
                "type": "rotation",
                "axis": "x",
                "value": value * 0.4  # 40% of movement in mid spine
            })
            mappings.append({
                "joint": "spine_03",
                "type": "rotation",
                "axis": "x",
                "value": value * 0.3  # 30% of movement in upper spine
            })
            
        # Direct mapping for GLB model parameters
        elif "_x_rotation" in param or "_y_rotation" in param or "_z_rotation" in param:
            parts = param.split("_")
            joint = "_".join(parts[:-2])  # Everything before _x_rotation
            axis = parts[-2][0]  # x, y, or z
            
            mappings.append({
                "joint": joint,
                "type": "rotation",
                "axis": axis,
                "value": value
            })
            
        elif "_x_position" in param or "_y_position" in param or "_z_position" in param:
            parts = param.split("_")
            joint = "_".join(parts[:-2])  # Everything before _x_position
            axis = parts[-2][0]  # x, y, or z
            
            mappings.append({
                "joint": joint,
                "type": "position",
                "axis": axis,
                "value": value
            })
            
        else:
            # Generic global parameter
            mappings.append({
                "global_param": param,
                "value": value
            })
        
        # Cache the mapping
        self.mapping_cache[cache_key] = mappings
        
        return mappings
    
    def _identify_significant_changes(self, optimized_params: Dict[str, float], original_params: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Identify significant changes between original and optimized parameters.
        
        Args:
            optimized_params: Optimized parameters
            original_params: Original parameters
            
        Returns:
            List of significant changes with descriptions
        """
        significant_changes = []
        
        for param in optimized_params:
            if param in original_params:
                # Calculate percentage change
                original = original_params[param]
                if original != 0:
                    change_pct = (optimized_params[param] - original) / abs(original) * 100
                    
                    # Consider significant if >10% change
                    if abs(change_pct) > 10:
                        change_info = {
                            "parameter": param,
                            "original_value": original,
                            "optimized_value": optimized_params[param],
                            "change_percentage": change_pct,
                            "direction": "increase" if change_pct > 0 else "decrease"
                        }
                        
                        # Add human-readable description
                        change_info["description"] = self._generate_change_description(
                            param, original, optimized_params[param], change_pct
                        )
                        
                        significant_changes.append(change_info)
        
        # Sort by absolute percentage change
        return sorted(significant_changes, key=lambda x: abs(x["change_percentage"]), reverse=True)
    
    def _generate_change_description(self, param: str, original: float, optimized: float, change_pct: float) -> str:
        """
        Generate a human-readable description of a parameter change.
        
        Args:
            param: Parameter name
            original: Original value
            optimized: Optimized value
            change_pct: Percentage change
            
        Returns:
            Human-readable description
        """
        direction = "increased" if change_pct > 0 else "decreased"
        magnitude = "significantly" if abs(change_pct) > 25 else "moderately" if abs(change_pct) > 15 else "slightly"
        
        # Format based on parameter type
        if "angle" in param or "flexion" in param or "extension" in param or "abduction" in param:
            return f"{param.replace('_', ' ').title()} {direction} {magnitude} from {original:.1f}° to {optimized:.1f}° ({abs(change_pct):.1f}%)"
        else:
            return f"{param.replace('_', ' ').title()} {direction} {magnitude} from {original:.2f} to {optimized:.2f} ({abs(change_pct):.1f}%)"
    
    def _load_skeleton_template(self) -> Dict[str, Any]:
        """
        Load the skeleton template for the GLB model.
        
        Returns:
            Skeleton template data
        """
        # In a real implementation, this would load from a file
        # Here, we'll define a simplified skeleton structure
        return {
            "joints": {
                "hip_r": {"parent": "pelvis", "type": "ball"},
                "knee_r": {"parent": "hip_r", "type": "hinge"},
                "ankle_r": {"parent": "knee_r", "type": "ball"},
                "hip_l": {"parent": "pelvis", "type": "ball"},
                "knee_l": {"parent": "hip_l", "type": "hinge"},
                "ankle_l": {"parent": "knee_l", "type": "ball"},
                "spine_01": {"parent": "pelvis", "type": "ball"},
                "spine_02": {"parent": "spine_01", "type": "ball"},
                "spine_03": {"parent": "spine_02", "type": "ball"},
                "neck": {"parent": "spine_03", "type": "ball"},
                "head": {"parent": "neck", "type": "ball"},
                "shoulder_r": {"parent": "spine_03", "type": "ball"},
                "elbow_r": {"parent": "shoulder_r", "type": "hinge"},
                "wrist_r": {"parent": "elbow_r", "type": "ball"},
                "shoulder_l": {"parent": "spine_03", "type": "ball"},
                "elbow_l": {"parent": "shoulder_l", "type": "hinge"},
                "wrist_l": {"parent": "elbow_l", "type": "ball"}
            },
            "default_pose": {
                "hip_r": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "knee_r": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "ankle_r": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "hip_l": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "knee_l": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "ankle_l": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "spine_01": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "spine_02": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "spine_03": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "neck": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "head": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "shoulder_r": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "elbow_r": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "wrist_r": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "shoulder_l": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "elbow_l": {"rotation": {"x": 0, "y": 0, "z": 0}},
                "wrist_l": {"rotation": {"x": 0, "y": 0, "z": 0}}
            }
        }
    
    def _load_animation_templates(self) -> Dict[str, Any]:
        """
        Load animation templates for common movements.
        
        Returns:
            Dictionary of animation templates
        """
        # In a real implementation, this would load from a file
        # Here, we'll define some simplified animation templates
        return {
            "squat": {
                "phases": ["descent", "bottom", "ascent"],
                "keyframes": {
                    "start": {
                        "hip_r": {"rotation": {"x": 0, "y": 0, "z": 0}},
                        "knee_r": {"rotation": {"x": 0, "y": -5, "z": 0}},
                        "hip_l": {"rotation": {"x": 0, "y": 0, "z": 0}},
                        "knee_l": {"rotation": {"x": 0, "y": -5, "z": 0}}
                    },
                    "bottom": {
                        "hip_r": {"rotation": {"x": 100, "y": 0, "z": 0}},
                        "knee_r": {"rotation": {"x": 0, "y": -120, "z": 0}},
                        "hip_l": {"rotation": {"x": 100, "y": 0, "z": 0}},
                        "knee_l": {"rotation": {"x": 0, "y": -120, "z": 0}}
                    },
                    "end": {
                        "hip_r": {"rotation": {"x": 0, "y": 0, "z": 0}},
                        "knee_r": {"rotation": {"x": 0, "y": -5, "z": 0}},
                        "hip_l": {"rotation": {"x": 0, "y": 0, "z": 0}},
                        "knee_l": {"rotation": {"x": 0, "y": -5, "z": 0}}
                    }
                }
            },
            "jump": {
                "phases": ["preparation", "takeoff", "flight", "landing"],
                "keyframes": {
                    "preparation": {
                        "hip_r": {"rotation": {"x": 45, "y": 0, "z": 0}},
                        "knee_r": {"rotation": {"x": 0, "y": -60, "z": 0}},
                        "hip_l": {"rotation": {"x": 45, "y": 0, "z": 0}},
                        "knee_l": {"rotation": {"x": 0, "y": -60, "z": 0}}
                    },
                    "takeoff": {
                        "hip_r": {"rotation": {"x": 15, "y": 0, "z": 0}},
                        "knee_r": {"rotation": {"x": 0, "y": -15, "z": 0}},
                        "hip_l": {"rotation": {"x": 15, "y": 0, "z": 0}},
                        "knee_l": {"rotation": {"x": 0, "y": -15, "z": 0}},
                        "ankle_r": {"rotation": {"x": 30, "y": 0, "z": 0}},
                        "ankle_l": {"rotation": {"x": 30, "y": 0, "z": 0}}
                    },
                    "flight": {
                        "hip_r": {"rotation": {"x": 10, "y": 0, "z": 0}},
                        "knee_r": {"rotation": {"x": 0, "y": -25, "z": 0}},
                        "hip_l": {"rotation": {"x": 10, "y": 0, "z": 0}},
                        "knee_l": {"rotation": {"x": 0, "y": -25, "z": 0}}
                    },
                    "landing": {
                        "hip_r": {"rotation": {"x": 45, "y": 0, "z": 0}},
                        "knee_r": {"rotation": {"x": 0, "y": -80, "z": 0}},
                        "hip_l": {"rotation": {"x": 45, "y": 0, "z": 0}},
                        "knee_l": {"rotation": {"x": 0, "y": -80, "z": 0}},
                        "ankle_r": {"rotation": {"x": 15, "y": 0, "z": 0}},
                        "ankle_l": {"rotation": {"x": 15, "y": 0, "z": 0}}
                    }
                }
            }
        } 