import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
import numpy as np
import sympy as sp
from scipy import optimize

from backend.llm.model_loader import get_biomech_llm

logger = logging.getLogger(__name__)

class BiomechanicalSolver:
    """
    Solver for biomechanical optimization problems.
    Uses a combination of numerical optimization and LLM reasoning.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the biomechanical solver.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.domain_llm = get_biomech_llm()
        self.optimization_methods = {
            "minimize_joint_stress": self._minimize_joint_stress,
            "maximize_power_output": self._maximize_power_output,
            "minimize_energy_expenditure": self._minimize_energy_expenditure
        }
        
        # Performance tracking
        self.last_optimization_time = 0
        self.last_llm_time = 0
        
        logger.info("Biomechanical solver initialized")
    
    def solve(self, structured_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solve the optimization problem defined in the structured query.
        
        Args:
            structured_query: Structured biomechanical query
            
        Returns:
            Solution with optimized parameters and explanation
        """
        logger.info("Solving biomechanical optimization problem...")
        start_time = time.time()
        
        # Extract key components from the query
        model_params = structured_query.get("model_params", {})
        constraints = structured_query.get("constraints", [])
        optimization_targets = structured_query.get("optimization_targets", {})
        intent = structured_query.get("intent", {})
        
        # Determine solution approach based on complexity and intent
        solution_approach = self._determine_solution_approach(structured_query)
        
        # Solve using the determined approach
        if solution_approach == "numerical_optimization":
            logger.info("Using numerical optimization approach")
            solution = self._solve_with_optimization(structured_query)
        elif solution_approach == "llm_reasoning":
            logger.info("Using LLM reasoning approach")
            solution = self._solve_with_llm(structured_query)
        else:  # "hybrid"
            logger.info("Using hybrid optimization approach")
            solution = self._solve_with_hybrid_approach(structured_query)
        
        # Add metadata to the solution
        solution["solution_approach"] = solution_approach
        solution["solving_time"] = time.time() - start_time
        
        logger.info(f"Solution found in {solution['solving_time']:.2f}s using {solution_approach}")
        return solution
    
    def _determine_solution_approach(self, query: Dict[str, Any]) -> str:
        """
        Determine the best solution approach based on query characteristics.
        
        Args:
            query: Structured biomechanical query
            
        Returns:
            Solution approach: "numerical_optimization", "llm_reasoning", or "hybrid"
        """
        # Extract factors that influence the decision
        intent = query.get("intent", {})
        optimization_targets = query.get("optimization_targets", {})
        model_params = query.get("model_params", {})
        constraints = query.get("constraints", [])
        
        # Check if we have well-defined numerical optimization criteria
        has_clear_objective = bool(optimization_targets.get("objective_function", ""))
        has_many_constraints = len(constraints) > 3
        has_many_params = len(model_params) > 5
        
        # Check if we need reasoning or explanation
        needs_reasoning = intent.get("primary_goal") in ["analysis", "correction"]
        has_qualitative_factors = "qualitative_factors" in str(query)
        
        # Decision logic
        if has_clear_objective and has_many_constraints and not needs_reasoning:
            return "numerical_optimization"
        elif (needs_reasoning or has_qualitative_factors) and not has_many_params:
            return "llm_reasoning"
        else:
            return "hybrid"
    
    def _solve_with_optimization(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solve using numerical optimization methods.
        
        Args:
            query: Structured biomechanical query
            
        Returns:
            Solution with optimized parameters
        """
        start_time = time.time()
        
        # Extract key components
        model_params = query.get("model_params", {})
        constraints = query.get("constraints", [])
        optimization_targets = query.get("optimization_targets", {})
        
        # Convert to optimization problem
        param_names = list(model_params.keys())
        param_values = np.array([model_params[name] for name in param_names])
        bounds = self._create_bounds(param_names, constraints)
        
        # Create the objective function
        objective_name = optimization_targets.get("objective_function", "minimize_joint_stress")
        if objective_name in self.optimization_methods:
            objective_func = self.optimization_methods[objective_name]
        else:
            # Default to joint stress minimization if not recognized
            objective_func = self._minimize_joint_stress
        
        # Prepare the objective function with weights
        weights = optimization_targets.get("weights", {})
        
        def objective(x):
            # Create parameter dictionary for the objective function
            params = {name: value for name, value in zip(param_names, x)}
            return objective_func(params, weights, query)
        
        # Create constraint functions
        constraint_funcs = self._create_constraint_functions(constraints, param_names)
        
        # Run optimization
        try:
            result = optimize.minimize(
                objective,
                param_values,
                method='SLSQP',
                bounds=bounds,
                constraints=constraint_funcs,
                options={'disp': True, 'maxiter': 100}
            )
            
            # Process results
            optimized_params = {name: value for name, value in zip(param_names, result.x)}
            
            # Calculate improvement metrics
            improvement = {
                param: (optimized_params[param] - model_params[param]) / model_params[param] * 100
                for param in model_params if model_params[param] != 0
            }
            
            # Generate basic explanation
            explanation = self._generate_optimization_explanation(
                optimized_params, model_params, improvement, objective_name
            )
            
            solution = {
                "optimized_params": optimized_params,
                "original_params": model_params,
                "improvement": improvement,
                "explanation": explanation,
                "optimization_details": {
                    "success": result.success,
                    "status": result.message,
                    "iterations": result.nit,
                    "function_evaluations": result.nfev,
                    "objective_value": result.fun
                }
            }
            
            self.last_optimization_time = time.time() - start_time
            return solution
            
        except Exception as e:
            logger.error(f"Optimization failed: {str(e)}")
            # Return original parameters if optimization fails
            return {
                "optimized_params": model_params,
                "original_params": model_params,
                "improvement": {},
                "explanation": f"Optimization failed due to: {str(e)}",
                "optimization_details": {
                    "success": False,
                    "status": str(e),
                    "error": str(e)
                }
            }
    
    def _solve_with_llm(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solve using domain LLM reasoning.
        
        Args:
            query: Structured biomechanical query
            
        Returns:
            Solution with optimized parameters and explanation
        """
        start_time = time.time()
        
        # Extract key components
        model_params = query.get("model_params", {})
        intent = query.get("intent", {})
        text_query = query.get("text", "")
        reference_data = query.get("reference_data", {})
        
        # Format prompt for the domain LLM
        prompt = self._format_solver_prompt(query)
        
        # Get response from LLM
        llm_response = self.domain_llm.generate(prompt=prompt, max_tokens=2048)
        
        # Extract parameters and explanation
        response_text = llm_response["text"]
        extracted_params = self._extract_parameters_from_text(response_text)
        
        # Merge extracted parameters with original ones (for any missing values)
        optimized_params = {**model_params}  # Start with original params
        optimized_params.update(extracted_params)  # Update with extracted ones
        
        # Calculate improvement
        improvement = {
            param: (optimized_params[param] - model_params[param]) / model_params[param] * 100
            for param in model_params 
            if param in optimized_params and model_params[param] != 0
        }
        
        solution = {
            "optimized_params": optimized_params,
            "original_params": model_params,
            "improvement": improvement,
            "explanation": response_text,
            "llm_details": {
                "model": llm_response.get("model", "unknown"),
                "tokens": llm_response.get("usage", {}).get("total_tokens", 0)
            }
        }
        
        self.last_llm_time = time.time() - start_time
        return solution
    
    def _solve_with_hybrid_approach(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solve using a hybrid approach combining numerical optimization and LLM reasoning.
        
        Args:
            query: Structured biomechanical query
            
        Returns:
            Solution with optimized parameters and explanation
        """
        # First, run numerical optimization
        optimization_result = self._solve_with_optimization(query)
        
        # Then, use LLM to analyze and refine the results
        # Create a modified query with the optimization results
        hybrid_query = {**query}
        hybrid_query["optimization_result"] = optimization_result
        hybrid_query["require_explanation"] = True
        
        # Get LLM analysis
        llm_result = self._solve_with_llm(hybrid_query)
        
        # Combine results, preferring numerical values from optimization
        # but using explanation and reasoning from LLM
        combined_params = optimization_result["optimized_params"]
        
        # For parameters where LLM significantly disagrees, use weighted average
        for param, llm_value in llm_result["optimized_params"].items():
            if param in combined_params:
                opt_value = combined_params[param]
                # If values differ significantly, use weighted blend
                if abs(llm_value - opt_value) / (abs(opt_value) + 1e-6) > 0.15:  # >15% difference
                    combined_params[param] = 0.7 * opt_value + 0.3 * llm_value
        
        # Create combined solution
        solution = {
            "optimized_params": combined_params,
            "original_params": query.get("model_params", {}),
            "improvement": optimization_result["improvement"],
            "explanation": llm_result["explanation"],
            "hybrid_details": {
                "optimization_contribution": 0.7,
                "llm_contribution": 0.3,
                "optimization_time": self.last_optimization_time,
                "llm_time": self.last_llm_time
            }
        }
        
        return solution
    
    def _create_bounds(self, param_names: List[str], constraints: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
        """
        Create bounds for optimization parameters based on constraints.
        
        Args:
            param_names: Names of parameters
            constraints: List of constraints
            
        Returns:
            List of (min, max) tuples for each parameter
        """
        # Default bounds (0, 1) for normalized parameters
        bounds = [(0, 1) for _ in param_names]
        
        # Update bounds based on constraints
        for i, param in enumerate(param_names):
            for constraint in constraints:
                if constraint.get("type") == "bound" and constraint.get("parameter") == param:
                    min_val = constraint.get("min", bounds[i][0])
                    max_val = constraint.get("max", bounds[i][1])
                    bounds[i] = (min_val, max_val)
        
        return bounds
    
    def _create_constraint_functions(self, constraints: List[Dict[str, Any]], param_names: List[str]) -> List[Dict[str, Any]]:
        """
        Create constraint functions for scipy.optimize.
        
        Args:
            constraints: List of constraints
            param_names: Names of parameters
            
        Returns:
            List of constraint dictionaries for scipy.optimize
        """
        constraint_funcs = []
        
        for constraint in constraints:
            if constraint.get("type") == "relationship" and constraint.get("expression"):
                # Parse relationship constraint using sympy
                expr = constraint.get("expression", "")
                
                try:
                    # Create sympy symbols for parameters
                    symbols = {name: sp.Symbol(name) for name in param_names}
                    
                    # Parse the expression
                    sympy_expr = sp.sympify(expr, locals=symbols)
                    
                    # Convert to constraint function
                    def make_constraint(expr, symbols, param_names):
                        def constraint_func(x):
                            # Map x values to named parameters
                            param_dict = {name: val for name, val in zip(param_names, x)}
                            # Substitute values into expression
                            result = float(expr.subs({sym: param_dict[name] for name, sym in symbols.items()}))
                            return result
                        return constraint_func
                    
                    constraint_funcs.append({
                        'type': 'ineq',
                        'fun': make_constraint(sympy_expr, symbols, param_names)
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to parse constraint expression '{expr}': {e}")
        
        return constraint_funcs
    
    def _minimize_joint_stress(self, params: Dict[str, float], weights: Dict[str, float], query: Dict[str, Any]) -> float:
        """
        Objective function to minimize joint stress.
        
        Args:
            params: Current parameter values
            weights: Weights for parameters
            query: Original query for context
            
        Returns:
            Objective function value (lower is better)
        """
        # A simplified joint stress model
        stress = 0.0
        
        # Joint angles contribute to stress when they approach limits
        joint_limits = {
            "knee_flexion_angle": (0, 160),
            "hip_flexion_angle": (0, 140),
            "ankle_dorsiflexion": (-20, 30),
            "shoulder_abduction": (0, 180)
            # Add more joints as needed
        }
        
        for joint, (min_val, max_val) in joint_limits.items():
            if joint in params:
                # Calculate normalized distance from center of range
                center = (min_val + max_val) / 2
                range_half = (max_val - min_val) / 2
                if range_half > 0:
                    # Penalize positions far from center (U-shaped stress curve)
                    normalized_dist = (params[joint] - center) / range_half
                    joint_stress = normalized_dist ** 2
                    # Apply weight if specified
                    joint_weight = weights.get(joint, 1.0)
                    stress += joint_stress * joint_weight
        
        # Add penalties for unfavorable joint relationships
        # Example: knee-hip ratio for safe lifting
        if "knee_flexion_angle" in params and "hip_flexion_angle" in params:
            knee_angle = params["knee_flexion_angle"]
            hip_angle = params["hip_flexion_angle"]
            if hip_angle > 0:
                knee_hip_ratio = knee_angle / hip_angle
                # Penalize if ratio is outside ideal range (0.7-1.3)
                if knee_hip_ratio < 0.7 or knee_hip_ratio > 1.3:
                    stress += 2.0 * min(abs(knee_hip_ratio - 0.7), abs(knee_hip_ratio - 1.3))
        
        return stress
    
    def _maximize_power_output(self, params: Dict[str, float], weights: Dict[str, float], query: Dict[str, Any]) -> float:
        """
        Objective function to maximize power output.
        
        Args:
            params: Current parameter values
            weights: Weights for parameters
            query: Original query for context
            
        Returns:
            Negative power output (lower is better for minimization)
        """
        # A simplified power output model
        power = 0.0
        
        # Optimal joint angles for power generation
        power_optima = {
            "knee_flexion_angle": 110,  # Degrees
            "hip_flexion_angle": 120,   # Degrees
            "ankle_dorsiflexion": 15,   # Degrees
            "shoulder_abduction": 90,   # Degrees
            "elbow_flexion": 100        # Degrees
        }
        
        # Calculate power contribution from each joint
        for joint, optimum in power_optima.items():
            if joint in params:
                # Power peaks at optimum angle and drops off with distance
                # Using a Gaussian-like function
                joint_power = np.exp(-0.5 * ((params[joint] - optimum) / 20) ** 2)
                # Apply weight if specified
                joint_weight = weights.get(joint, 1.0)
                power += joint_power * joint_weight
        
        # Return negative because we're minimizing
        return -power
    
    def _minimize_energy_expenditure(self, params: Dict[str, float], weights: Dict[str, float], query: Dict[str, Any]) -> float:
        """
        Objective function to minimize energy expenditure.
        
        Args:
            params: Current parameter values
            weights: Weights for parameters
            query: Original query for context
            
        Returns:
            Energy expenditure (lower is better)
        """
        # A simplified energy expenditure model
        energy = 0.0
        
        # Baseline metabolic cost
        baseline = 1.0
        
        # Joint inefficiency factors (positions that require more energy)
        inefficiency_factors = {
            "knee_flexion_angle": lambda x: 0.01 * x,  # Deep knee bends cost more energy
            "hip_flexion_angle": lambda x: 0.01 * x,   # Hip flexion costs energy
            "shoulder_abduction": lambda x: 0.005 * x  # Raised arms cost energy
        }
        
        # Calculate energy cost for each joint position
        for joint, factor_func in inefficiency_factors.items():
            if joint in params:
                # Calculate energy cost for this joint
                joint_energy = factor_func(params[joint])
                # Apply weight if specified
                joint_weight = weights.get(joint, 1.0)
                energy += joint_energy * joint_weight
        
        # Penalize overall deviation from neutral stance
        neutral_stance = {
            "knee_flexion_angle": 5,    # Nearly straight
            "hip_flexion_angle": 5,     # Nearly straight
            "ankle_dorsiflexion": 0,    # Neutral
            "shoulder_abduction": 0,    # By sides
            "elbow_flexion": 10         # Slightly bent
        }
        
        # Calculate deviation energy cost
        deviation_cost = sum(
            ((params.get(joint, 0) - neutral) / 90) ** 2  # Normalized by 90 degrees
            for joint, neutral in neutral_stance.items()
            if joint in params
        )
        
        # Add weighted deviation cost
        energy += deviation_cost * weights.get("posture_deviation", 0.5)
        
        # Add baseline metabolic cost
        energy += baseline
        
        return energy
    
    def _generate_optimization_explanation(self, 
                                       optimized_params: Dict[str, float], 
                                       original_params: Dict[str, float],
                                       improvement: Dict[str, float],
                                       objective_name: str) -> str:
        """
        Generate a basic explanation of optimization results.
        
        Args:
            optimized_params: Optimized parameters
            original_params: Original parameters
            improvement: Percentage improvement by parameter
            objective_name: Name of the objective function
            
        Returns:
            Explanation text
        """
        # Create explanation based on the objective
        if objective_name == "minimize_joint_stress":
            explanation = "Optimization focused on reducing joint stress by adjusting posture."
        elif objective_name == "maximize_power_output":
            explanation = "Optimization focused on maximizing power output through optimal joint angles."
        elif objective_name == "minimize_energy_expenditure":
            explanation = "Optimization focused on improving movement efficiency and reducing energy cost."
        else:
            explanation = f"Optimization completed using {objective_name} objective."
        
        # Add detail on most significant changes
        significant_changes = sorted(
            [(param, pct) for param, pct in improvement.items() if abs(pct) > 5],
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        if significant_changes:
            explanation += "\n\nMost significant changes:"
            for param, pct in significant_changes[:3]:  # Top 3 changes
                direction = "increased" if pct > 0 else "decreased"
                explanation += f"\n- {param} {direction} by {abs(pct):.1f}% (from {original_params[param]:.1f} to {optimized_params[param]:.1f})"
        
        return explanation
    
    def _format_solver_prompt(self, query: Dict[str, Any]) -> str:
        """
        Format a prompt for the domain LLM to solve the problem.
        
        Args:
            query: Structured biomechanical query
            
        Returns:
            Formatted prompt
        """
        model_params = query.get("model_params", {})
        text_query = query.get("text", "")
        intent = query.get("intent", {})
        
        # Format the prompt
        prompt = f"""
        As a biomechanical analysis expert, optimize the following movement parameters:
        
        USER QUERY: {text_query}
        
        CURRENT PARAMETERS:
        """
        
        # Add current parameters
        for param, value in model_params.items():
            prompt += f"- {param}: {value}\n"
        
        # Add intent information
        prompt += f"\nPRIMARY GOAL: {intent.get('primary_goal', 'analysis')}\n"
        prompt += f"FOCUS AREAS: {', '.join(intent.get('focus_areas', ['overall posture']))}\n"
        prompt += f"OPTIMIZATION TYPE: {intent.get('optimization_type', 'performance')}\n"
        
        # Add optimization result if this is a hybrid approach
        if "optimization_result" in query:
            prompt += "\nNUMERICAL OPTIMIZATION SUGGESTED THESE VALUES:\n"
            opt_params = query["optimization_result"].get("optimized_params", {})
            for param, value in opt_params.items():
                prompt += f"- {param}: {value}\n"
        
        # Add specific instructions
        prompt += """
        INSTRUCTIONS:
        1. Analyze the current parameters and suggest optimal values
        2. Provide a brief explanation for each significant change
        3. Consider biomechanical principles and safety
        4. Format parameter suggestions as "parameter: value"
        5. Explain the biomechanical reasoning behind your suggestions
        """
        
        return prompt
    
    def _extract_parameters_from_text(self, text: str) -> Dict[str, float]:
        """
        Extract parameter values from LLM response text.
        
        Args:
            text: Response text from LLM
            
        Returns:
            Dictionary of parameter values
        """
        import re
        
        # Find all parameter: value pairs using regex
        param_pattern = r'([a-zA-Z_]+)[:\s]+([0-9.]+)'
        matches = re.findall(param_pattern, text)
        
        # Convert to dictionary with float values
        return {param.strip(): float(value) for param, value in matches} 