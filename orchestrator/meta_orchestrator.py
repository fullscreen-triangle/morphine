import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
import numpy as np

# For LLM integrations
import openai
from anthropic import Anthropic
from backend.llm.model_loader import get_biomech_llm

# For metrics and decision making
from sklearn.metrics import mean_squared_error
import scipy.optimize as optimize

logger = logging.getLogger(__name__)

class MetaOrchestrator:
    """
    Metacognitive orchestrator that manages the entire pipeline.
    Makes intelligent decisions about which tools to use for different tasks.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the meta orchestrator with configuration.
        
        Args:
            config: Configuration dictionary containing API keys, thresholds, etc.
        """
        self.config = config
        
        # Initialize LLM clients
        self.openai_client = openai.OpenAI(api_key=config.get("openai_api_key"))
        self.anthropic_client = Anthropic(api_key=config.get("anthropic_api_key"))
        self.domain_llm = get_biomech_llm()
        
        # Complexity thresholds for decision making
        self.complexity_threshold = config.get("complexity_threshold", 0.7)
        self.precision_threshold = config.get("precision_threshold", 0.85)
        
        # Cache for optimizations
        self.optimization_cache = {}
        
        logger.info("Meta orchestrator initialized")
    
    def process_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a posture query through the entire pipeline.
        
        Args:
            query: Dict containing query parameters including:
                - text: User's natural language query
                - model_params: Parameters from the GLB model interaction
                - constraints: Any physical constraints to consider
                
        Returns:
            Dict containing the results of the query
        """
        start_time = time.time()
        logger.info(f"Processing query: {query.get('text', '')[:100]}...")
        
        # Step 1: Analyze query complexity and type
        query_analysis = self._analyze_query(query)
        
        # Step 2: Choose optimal processing path based on analysis
        if query_analysis["requires_commercial_llm"]:
            # Use commercial LLM for complex reasoning
            if query_analysis["preferred_llm"] == "claude":
                processed_query = self._process_with_claude(query, query_analysis)
            else:
                processed_query = self._process_with_openai(query, query_analysis)
        else:
            # Use domain LLM or direct solvers
            if query_analysis["requires_optimization"]:
                processed_query = self._process_with_optimizer(query, query_analysis)
            else:
                processed_query = self._process_with_domain_llm(query, query_analysis)
        
        # Step 3: Validate results
        validated_results = self._validate_results(processed_query)
        
        # Step 4: Format for output
        final_results = self._format_results(validated_results)
        
        processing_time = time.time() - start_time
        logger.info(f"Query processed in {processing_time:.2f}s using {query_analysis['processing_path']}")
        
        # Include metacognitive insights
        final_results["meta"] = {
            "processing_time": processing_time,
            "processing_path": query_analysis["processing_path"],
            "confidence": validated_results["confidence"],
            "alternatives_considered": validated_results.get("alternatives", [])
        }
        
        return final_results
    
    def _analyze_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the query to determine its complexity and the best processing path.
        
        Args:
            query: The user query
            
        Returns:
            Dict with analysis results
        """
        # Extract key information
        text = query.get("text", "")
        model_params = query.get("model_params", {})
        complexity_score = self._calculate_complexity(text, model_params)
        
        # Determine if query requires optimization
        requires_optimization = (
            "optimize" in text.lower() or
            "best" in text.lower() or
            "efficient" in text.lower() or
            len(model_params) > 5  # Complex parameter space
        )
        
        # Determine if commercial LLM is needed
        requires_commercial_llm = (
            complexity_score > self.complexity_threshold or
            "explain" in text.lower() or
            "compare" in text.lower() or
            "why" in text.lower()
        )
        
        # Choose preferred commercial LLM
        preferred_llm = "claude" if "reasoning" in text.lower() or complexity_score > 0.85 else "openai"
        
        # Determine processing path
        if requires_commercial_llm:
            processing_path = f"commercial_llm_{preferred_llm}"
        elif requires_optimization:
            processing_path = "python_optimizer"
        else:
            processing_path = "domain_llm"
        
        return {
            "complexity_score": complexity_score,
            "requires_optimization": requires_optimization,
            "requires_commercial_llm": requires_commercial_llm,
            "preferred_llm": preferred_llm,
            "processing_path": processing_path
        }
    
    def _calculate_complexity(self, text: str, model_params: Dict[str, Any]) -> float:
        """
        Calculate the complexity score of a query.
        
        Args:
            text: Query text
            model_params: Model parameters
            
        Returns:
            Complexity score between 0-1
        """
        # Text complexity factors
        text_length = min(1.0, len(text) / 200)  # Normalize
        question_count = text.count("?") / 3
        technical_terms = sum(1 for term in [
            "biomechanical", "kinematic", "kinetic", "angular", "velocity",
            "acceleration", "torque", "force", "momentum", "vector"
        ] if term in text.lower()) / 10
        
        # Parameter complexity
        param_complexity = min(1.0, len(model_params) / 10)
        
        # Calculate weighted score
        complexity_score = (
            0.3 * text_length +
            0.2 * question_count +
            0.3 * technical_terms +
            0.2 * param_complexity
        )
        
        return min(1.0, complexity_score)
    
    def _process_with_claude(self, query: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process query using Anthropic Claude"""
        response = self.anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": self._format_llm_prompt(query, analysis, "claude")
                }
            ]
        )
        
        # Extract and parse Claude's response
        return self._parse_llm_response(response.content[0].text, "claude")
    
    def _process_with_openai(self, query: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process query using OpenAI"""
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a biomechanical analysis expert."},
                {"role": "user", "content": self._format_llm_prompt(query, analysis, "openai")}
            ],
            max_tokens=2000
        )
        
        # Extract and parse OpenAI's response
        return self._parse_llm_response(response.choices[0].message.content, "openai")
    
    def _process_with_domain_llm(self, query: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process query using domain-specific LLM"""
        prompt = self._format_domain_llm_prompt(query, analysis)
        response = self.domain_llm.generate(prompt=prompt)
        
        return {
            "response": response["text"],
            "model_params": self._extract_model_params(response["text"]),
            "confidence": 0.85,  # Domain LLM typically has high confidence in its specialty
            "source": "domain_llm"
        }
    
    def _process_with_optimizer(self, query: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process query using Python optimization tools"""
        # Convert query to optimization problem
        objective_function, constraints, bounds = self._formulate_optimization(query)
        
        # Generate optimization cache key
        cache_key = str(hash(f"{query.get('text', '')}_{str(query.get('model_params', {}))}"))
        
        # Check cache first
        if cache_key in self.optimization_cache:
            logger.info("Using cached optimization result")
            return self.optimization_cache[cache_key]
        
        # Run optimization
        try:
            result = optimize.minimize(
                objective_function,
                x0=np.zeros(len(bounds)),
                bounds=bounds,
                constraints=constraints
            )
            
            optimized_params = self._convert_optimization_result(result)
            confidence = 1.0 if result.success else 0.6
            
            response = {
                "response": f"Optimized solution found with objective value: {result.fun:.4f}",
                "model_params": optimized_params,
                "optimization_details": {
                    "success": result.success,
                    "iterations": result.nit,
                    "objective_value": result.fun
                },
                "confidence": confidence,
                "source": "python_optimizer"
            }
            
            # Cache successful results
            if result.success:
                self.optimization_cache[cache_key] = response
                
            return response
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            # Fallback to domain LLM
            return self._process_with_domain_llm(query, analysis)
    
    def _formulate_optimization(self, query: Dict[str, Any]) -> Tuple[callable, List, List[Tuple]]:
        """
        Formulate the optimization problem from the query.
        
        Returns:
            Tuple containing:
            - objective function
            - constraints list
            - bounds list
        """
        # Extract model parameters to optimize
        model_params = query.get("model_params", {})
        param_names = list(model_params.keys())
        
        # Default bounds if not specified
        bounds = [(0, 1) for _ in param_names]
        
        # Simple example objective function - would be more complex in reality
        def objective_function(x):
            # Map x values to named parameters
            params = {name: value for name, value in zip(param_names, x)}
            
            # Evaluate biomechanical efficiency - simplified example
            # In reality, this would use physics-based calculations
            efficiency = sum(
                (value - model_params.get(name, 0.5))**2 
                for name, value in params.items()
            )
            
            return efficiency
        
        # Example constraints - would be based on biomechanical principles
        constraints = []
        
        return objective_function, constraints, bounds
    
    def _convert_optimization_result(self, result) -> Dict[str, float]:
        """Convert optimization result to model parameters"""
        # Implementation depends on the specific optimization problem
        return {"param1": result.x[0], "param2": result.x[1]} if len(result.x) > 1 else {"param": result.x[0]}
    
    def _format_llm_prompt(self, query: Dict[str, Any], analysis: Dict[str, Any], llm_type: str) -> str:
        """Format prompt for commercial LLMs with specific instructions"""
        base_prompt = f"""
        You are a biomechanical expert specializing in human movement analysis.
        
        USER QUERY:
        {query.get('text', '')}
        
        CURRENT MODEL PARAMETERS:
        {query.get('model_params', {})}
        
        CONSTRAINTS:
        {query.get('constraints', [])}
        
        Please analyze this query and provide:
        1. A detailed explanation of the optimal posture/movement
        2. Specific adjustments to the model parameters
        3. Biomechanical reasoning for your recommendations
        4. Confidence level in your analysis (0-1 scale)
        
        FORMAT YOUR RESPONSE AS JSON:
        ```json
        {
            "explanation": "Your detailed explanation here",
            "model_params": {"param1": value1, "param2": value2, ...},
            "reasoning": "Your biomechanical reasoning here",
            "confidence": 0.X
        }
        ```
        """
        
        # Add LLM-specific instructions
        if llm_type == "claude":
            base_prompt += "\nFocus on providing detailed biomechanical reasoning and principles."
        elif llm_type == "openai":
            base_prompt += "\nFocus on providing practical, actionable parameter adjustments."
            
        return base_prompt
    
    def _format_domain_llm_prompt(self, query: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Format prompt specifically for domain LLM"""
        return f"""
        Analyze biomechanics for: {query.get('text', '')}
        
        Current parameters:
        {query.get('model_params', {})}
        
        Provide optimal parameters and brief explanation.
        """
    
    def _parse_llm_response(self, response_text: str, llm_type: str) -> Dict[str, Any]:
        """Parse and extract structured data from LLM response"""
        try:
            # Extract JSON if present
            import json
            import re
            
            json_pattern = r'```json\s*(.*?)\s*```'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
                parsed_data = json.loads(json_str)
                parsed_data["source"] = llm_type
                return parsed_data
            else:
                # Fallback to extraction heuristics
                model_params = self._extract_model_params(response_text)
                return {
                    "response": response_text,
                    "model_params": model_params,
                    "confidence": 0.7,  # Default confidence when structure is unclear
                    "source": llm_type
                }
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {
                "response": response_text,
                "model_params": {},
                "confidence": 0.5,
                "source": llm_type,
                "parse_error": str(e)
            }
    
    def _extract_model_params(self, text: str) -> Dict[str, float]:
        """Extract model parameters from text"""
        import re
        
        # Look for parameter patterns like "parameter: value" or "parameter = value"
        param_pattern = r'(\w+)[\s]*[:=][\s]*([\d.]+)'
        matches = re.findall(param_pattern, text)
        
        return {param: float(value) for param, value in matches}
    
    def _validate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate results and adjust confidence if needed"""
        # Check if parameters are within physical limits
        model_params = results.get("model_params", {})
        
        # Physical validation checks would go here
        physical_validity = self._check_physical_validity(model_params)
        
        # Adjust confidence based on physical validity
        if not physical_validity["valid"]:
            results["confidence"] = results.get("confidence", 1.0) * 0.7
            results["validation_issues"] = physical_validity["issues"]
        
        return results
    
    def _check_physical_validity(self, params: Dict[str, float]) -> Dict[str, Any]:
        """Check if parameters are physically valid"""
        # This would contain biomechanical validation rules
        issues = []
        
        # Example check (simplified)
        if "knee_angle" in params and (params["knee_angle"] < 0 or params["knee_angle"] > 180):
            issues.append("Knee angle outside physiological range (0-180 degrees)")
            
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def _format_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Format results for output to the frontend"""
        # Create a clean, structured output
        return {
            "posture_params": results.get("model_params", {}),
            "explanation": results.get("response", ""),
            "confidence": results.get("confidence", 0.0),
            "source": results.get("source", "unknown"),
            "validation_issues": results.get("validation_issues", [])
        } 