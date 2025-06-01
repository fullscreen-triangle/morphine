import os
import sys
import logging
from pathlib import Path

# Add the backend directory to the path
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# Import backend components
from backend.api.routes import router as backend_router
from backend.config.settings import API_HOST, API_PORT, CORS_ORIGINS, DEBUG

# Import orchestration components
from orchestration.meta_orchestrator import MetaOrchestrator
from orchestration.query_processor import QueryProcessor
from orchestration.solver import BiomechanicalSolver
from orchestration.interpreter import GlbInterpreter
from orchestration.rag_engine import BiomechanicalRAG

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("orchestration")

# Create FastAPI app
app = FastAPI(
    title="VisualKinetics API",
    description="API for biomechanical analysis of sports videos",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestration components
config = {
    "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
    "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    "complexity_threshold": 0.7,
    "precision_threshold": 0.85,
    "knowledge_base_path": "data/knowledge_base"
}

meta_orchestrator = MetaOrchestrator(config)
query_processor = QueryProcessor(config)
biomech_solver = BiomechanicalSolver(config)
glb_interpreter = GlbInterpreter(config)
biomech_rag = BiomechanicalRAG(config)

# Define request models
class PostureQueryRequest(BaseModel):
    text_query: str
    glb_interaction: Dict[str, Any]
    constraints: Optional[Dict[str, Any]] = None

class QueryAnalysisRequest(BaseModel):
    analysis_id: str
    query: str

class KnowledgeDocumentRequest(BaseModel):
    documents: List[Dict[str, Any]]
    category: Optional[str] = "user_added"

class FeedbackRequest(BaseModel):
    query_id: str
    feedback_text: str
    rating: int
    improved_parameters: Optional[Dict[str, float]] = None

# Include backend API routes
app.include_router(backend_router, prefix="/api")

# Define posture query endpoint
@app.post("/api/posture/query", response_model=Dict[str, Any])
async def query_posture(request: PostureQueryRequest):
    """
    Process a posture query from the GLB model frontend and return optimized posture.
    """
    try:
        logger.info(f"Received posture query: {request.text_query[:100]}...")
        
        # Process through metacognitive orchestrator
        result = meta_orchestrator.process_query({
            "text": request.text_query,
            "model_params": request.glb_interaction.get("pose_data", {}),
            "constraints": request.constraints
        })
        
        return result
    except Exception as e:
        logger.error(f"Error processing posture query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/posture/process", response_model=Dict[str, Any])
async def process_posture_query(request: PostureQueryRequest):
    """
    Process a posture query step by step through the pipeline components.
    Shows the intermediate results for debugging and explanation.
    """
    try:
        logger.info(f"Processing posture query step by step: {request.text_query[:100]}...")
        
        # Step 1: Process the query
        structured_query = query_processor.process_user_input(
            request.text_query,
            request.glb_interaction,
            request.constraints
        )
        
        # Step 2: Retrieve relevant domain knowledge using RAG
        domain_context = biomech_rag.generate_context(
            request.text_query,
            structured_query.get("model_params", {})
        )
        structured_query["domain_context"] = domain_context
        
        # Step 3: Solve the optimization problem
        solution = biomech_solver.solve(structured_query)
        
        # Step 4: Interpret the solution back to GLB model
        glb_updates = glb_interpreter.interpret(solution, structured_query)
        
        # Return all intermediate results for transparency
        return {
            "structured_query": structured_query,
            "solution": solution,
            "glb_updates": glb_updates,
            "processing_time": {
                "total": solution.get("solving_time", 0)
            }
        }
    except Exception as e:
        logger.error(f"Error in step-by-step processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/add", response_model=Dict[str, Any])
async def add_knowledge(request: KnowledgeDocumentRequest):
    """
    Add new knowledge documents to the biomechanical knowledge base.
    """
    try:
        logger.info(f"Adding {len(request.documents)} new knowledge documents")
        
        # Add documents to the knowledge base
        biomech_rag.index_documents(request.documents, request.category)
        
        return {
            "success": True,
            "message": f"Added {len(request.documents)} documents to the knowledge base",
            "count": len(request.documents)
        }
    except Exception as e:
        logger.error(f"Error adding knowledge documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/retrieve", response_model=List[Dict[str, Any]])
async def retrieve_knowledge(query: str = Body(..., embed=True), filters: Optional[Dict[str, Any]] = Body(None, embed=True)):
    """
    Retrieve knowledge documents relevant to a query.
    """
    try:
        logger.info(f"Retrieving knowledge for query: {query[:100]}...")
        
        # Retrieve documents from the knowledge base
        results = biomech_rag.retrieve(query, filters)
        
        return results
    except Exception as e:
        logger.error(f"Error retrieving knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/templates/retrieve", response_model=List[Dict[str, Any]])
async def retrieve_templates(movement_type: str = Body(..., embed=True)):
    """
    Retrieve posture templates for a specific movement type.
    """
    try:
        logger.info(f"Retrieving templates for movement: {movement_type}")
        
        # Retrieve templates from the knowledge base
        templates = biomech_rag.retrieve_posture_templates(movement_type)
        
        return templates
    except Exception as e:
        logger.error(f"Error retrieving templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/feedback/submit", response_model=Dict[str, Any])
async def submit_feedback(request: FeedbackRequest):
    """
    Submit user feedback for a query to improve the system.
    """
    try:
        logger.info(f"Receiving feedback for query ID: {request.query_id}")
        
        # Format and export the feedback
        feedback_data = {
            "query_id": request.query_id,
            "feedback_text": request.feedback_text,
            "rating": request.rating,
            "improved_parameters": request.improved_parameters,
            "timestamp": str(import_datetime.datetime.now())
        }
        
        biomech_rag.export_feedback(feedback_data)
        
        return {
            "success": True,
            "message": "Feedback submitted successfully"
        }
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "services": {
        "meta_orchestrator": isinstance(meta_orchestrator, MetaOrchestrator),
        "query_processor": isinstance(query_processor, QueryProcessor),
        "biomech_solver": isinstance(biomech_solver, BiomechanicalSolver),
        "glb_interpreter": isinstance(glb_interpreter, GlbInterpreter),
        "biomech_rag": isinstance(biomech_rag, BiomechanicalRAG)
    }}

# Serve frontend in production
if not DEBUG:
    frontend_path = Path(__file__).resolve().parent.parent / "frontend" / "out"
    if frontend_path.exists():
        app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
        
        @app.get("/{path:path}", include_in_schema=False)
        async def serve_frontend(path: str):
            frontend_file = frontend_path / path
            if frontend_file.exists() and frontend_file.is_file():
                return FileResponse(str(frontend_file))
            return FileResponse(str(frontend_path / "index.html"))
    else:
        logger.warning(f"Frontend build directory not found at {frontend_path}")

def start_server():
    """Start the orchestration server"""
    logger.info(f"Starting VisualKinetics server on {API_HOST}:{API_PORT}")
    uvicorn.run(
        "orchestration.server:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info",
    )

if __name__ == "__main__":
    start_server()
