import logging
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# For vector embeddings
try:
    import torch
    from sentence_transformers import SentenceTransformer
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logger = logging.getLogger(__name__)

class BiomechanicalRAG:
    """
    Retrieval-Augmented Generation system for biomechanical domain knowledge.
    Provides domain context for LLMs to make more informed optimization decisions.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the biomechanical RAG system.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.knowledge_base_path = Path(config.get("knowledge_base_path", "data/knowledge_base"))
        self.embedding_model_name = config.get("embedding_model", "all-MiniLM-L6-v2")
        self.embedding_dimension = config.get("embedding_dimension", 384)
        self.top_k = config.get("top_k", 5)
        
        # Initialize embedding model
        self.embedding_model = self._initialize_embedding_model()
        
        # Load knowledge base
        self.documents = []
        self.document_embeddings = []
        self.document_metadata = []
        self._load_knowledge_base()
        
        logger.info(f"Biomechanical RAG initialized with {len(self.documents)} documents")
    
    def _initialize_embedding_model(self):
        """Initialize the embedding model for semantic search"""
        if not HAS_TORCH:
            logger.warning("PyTorch or sentence-transformers not available. Using fallback embedding method.")
            return None
            
        try:
            model = SentenceTransformer(self.embedding_model_name)
            return model
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            return None
    
    def _load_knowledge_base(self):
        """Load documents from the knowledge base directory"""
        if not self.knowledge_base_path.exists():
            logger.warning(f"Knowledge base path does not exist: {self.knowledge_base_path}")
            os.makedirs(self.knowledge_base_path, exist_ok=True)
            return
        
        # Check for pre-computed embeddings
        embedding_path = self.knowledge_base_path / "embeddings.npy"
        metadata_path = self.knowledge_base_path / "metadata.json"
        
        if embedding_path.exists() and metadata_path.exists():
            try:
                # Load pre-computed embeddings and metadata
                self.document_embeddings = np.load(str(embedding_path))
                
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    self.document_metadata = metadata.get("metadata", [])
                    self.documents = metadata.get("documents", [])
                
                logger.info(f"Loaded {len(self.documents)} documents with pre-computed embeddings")
                return
            except Exception as e:
                logger.error(f"Failed to load pre-computed embeddings: {e}")
        
        # If no pre-computed embeddings, load and process documents
        for file_path in self.knowledge_base_path.glob("*.json"):
            if file_path.name in ["embeddings.npy", "metadata.json"]:
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = json.load(f)
                    
                    # Process each document in the file
                    if isinstance(content, list):
                        for doc in content:
                            self._process_document(doc, file_path.stem)
                    else:
                        self._process_document(content, file_path.stem)
            except Exception as e:
                logger.error(f"Failed to load knowledge base file {file_path}: {e}")
        
        # Compute embeddings for all documents
        self._compute_embeddings()
        
        # Save embeddings and metadata
        self._save_embeddings()
    
    def _process_document(self, doc: Dict[str, Any], source: str):
        """Process a document from the knowledge base"""
        text = ""
        
        # Extract text content from document based on its structure
        if "text" in doc:
            text = doc["text"]
        elif "content" in doc:
            text = doc["content"]
        elif "description" in doc:
            text = doc["description"]
        
        # Add title if available
        if "title" in doc:
            text = f"{doc['title']}\n\n{text}"
        
        # Store document text and metadata
        if text:
            self.documents.append(text)
            
            # Extract and store metadata
            metadata = {
                "source": source,
                "type": doc.get("type", "unknown"),
                "category": doc.get("category", "general"),
            }
            
            # Add specific biomechanical metadata if available
            if "joint" in doc:
                metadata["joint"] = doc["joint"]
            if "movement" in doc:
                metadata["movement"] = doc["movement"]
            
            self.document_metadata.append(metadata)
    
    def _compute_embeddings(self):
        """Compute embeddings for all documents"""
        if not self.documents:
            logger.warning("No documents to compute embeddings for")
            return
            
        if self.embedding_model:
            # Use sentence-transformers for embeddings
            try:
                logger.info(f"Computing embeddings for {len(self.documents)} documents")
                self.document_embeddings = self.embedding_model.encode(self.documents)
                logger.info(f"Computed embeddings with shape {self.document_embeddings.shape}")
            except Exception as e:
                logger.error(f"Failed to compute embeddings: {e}")
                # Fall back to simple TF-IDF like approach
                self._compute_simple_embeddings()
        else:
            # Use simple TF-IDF like approach if no model available
            self._compute_simple_embeddings()
    
    def _compute_simple_embeddings(self):
        """Compute simple embeddings based on keyword presence"""
        # Define biomechanical keywords for embedding
        keywords = [
            "knee", "hip", "ankle", "shoulder", "elbow", "wrist", "spine", "neck",
            "flexion", "extension", "abduction", "adduction", "rotation", "force",
            "torque", "power", "velocity", "acceleration", "momentum", "balance",
            "stability", "range of motion", "biomechanics", "kinetics", "kinematics",
            "gait", "posture", "ergonomics", "joint", "muscle", "tendon", "ligament"
        ]
        
        # Create simple embeddings based on keyword presence
        embeddings = []
        for doc in self.documents:
            doc_lower = doc.lower()
            embedding = [1 if keyword in doc_lower else 0 for keyword in keywords]
            embeddings.append(embedding)
        
        self.document_embeddings = np.array(embeddings)
        
        # If all zeros, use random embeddings
        if np.all(self.document_embeddings == 0):
            self.document_embeddings = np.random.rand(len(self.documents), len(keywords))
            logger.warning("Using random embeddings as fallback")
    
    def _save_embeddings(self):
        """Save embeddings and metadata for future use"""
        if not self.document_embeddings.any() or not self.documents:
            return
            
        try:
            embedding_path = self.knowledge_base_path / "embeddings.npy"
            metadata_path = self.knowledge_base_path / "metadata.json"
            
            # Save embeddings
            np.save(str(embedding_path), self.document_embeddings)
            
            # Save metadata and documents
            metadata = {
                "metadata": self.document_metadata,
                "documents": self.documents
            }
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
                
            logger.info(f"Saved embeddings and metadata for {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Failed to save embeddings: {e}")
    
    def retrieve(self, query: str, filters: Optional[Dict[str, Any]] = None, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Query text
            filters: Optional filters for document selection
            top_k: Number of documents to retrieve (defaults to self.top_k)
            
        Returns:
            List of retrieved documents with metadata and similarity scores
        """
        if not self.documents or not self.document_embeddings.any():
            return []
            
        if top_k is None:
            top_k = self.top_k
            
        # Get query embedding
        query_embedding = self._get_embedding(query)
        
        # Apply pre-filters if specified
        indices = self._apply_filters(filters)
        
        # Calculate similarities between query and documents
        if len(indices) > 0:
            filtered_embeddings = self.document_embeddings[indices]
            similarities = cosine_similarity([query_embedding], filtered_embeddings)[0]
            
            # Get top-k documents
            top_indices = similarities.argsort()[-top_k:][::-1]
            
            # Map back to original indices
            top_indices = [indices[i] for i in top_indices]
        else:
            similarities = cosine_similarity([query_embedding], self.document_embeddings)[0]
            top_indices = similarities.argsort()[-top_k:][::-1]
        
        # Build result
        results = []
        for i, idx in enumerate(top_indices):
            results.append({
                "document": self.documents[idx],
                "metadata": self.document_metadata[idx],
                "similarity": float(similarities[i])
            })
        
        return results
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a text"""
        if self.embedding_model:
            try:
                return self.embedding_model.encode(text)
            except Exception as e:
                logger.error(f"Failed to get embedding: {e}")
                return self._get_simple_embedding(text)
        else:
            return self._get_simple_embedding(text)
    
    def _get_simple_embedding(self, text: str) -> np.ndarray:
        """Get simple embedding based on keyword presence"""
        keywords = [
            "knee", "hip", "ankle", "shoulder", "elbow", "wrist", "spine", "neck",
            "flexion", "extension", "abduction", "adduction", "rotation", "force",
            "torque", "power", "velocity", "acceleration", "momentum", "balance",
            "stability", "range of motion", "biomechanics", "kinetics", "kinematics",
            "gait", "posture", "ergonomics", "joint", "muscle", "tendon", "ligament"
        ]
        
        text_lower = text.lower()
        embedding = [1 if keyword in text_lower else 0 for keyword in keywords]
        
        return np.array(embedding)
    
    def _apply_filters(self, filters: Optional[Dict[str, Any]]) -> List[int]:
        """
        Apply filters to document selection.
        
        Args:
            filters: Dictionary of filters to apply
            
        Returns:
            List of indices of matching documents
        """
        if not filters:
            return list(range(len(self.documents)))
            
        indices = []
        for i, metadata in enumerate(self.document_metadata):
            match = True
            
            for key, value in filters.items():
                if key not in metadata or metadata[key] != value:
                    match = False
                    break
                    
            if match:
                indices.append(i)
                
        return indices
    
    def generate_context(self, query: str, biomech_params: Dict[str, float]) -> str:
        """
        Generate context for LLM by retrieving relevant documents.
        
        Args:
            query: Query text
            biomech_params: Current biomechanical parameters
            
        Returns:
            Generated context as text
        """
        # Extract key joints and movements from query and parameters
        focus_filters = self._extract_focus_from_query(query, biomech_params)
        
        # Retrieve general biomechanical knowledge
        general_results = self.retrieve(query, top_k=2)
        
        # Retrieve joint-specific knowledge
        joint_results = []
        if "joint" in focus_filters:
            joint_filters = {"joint": focus_filters["joint"]}
            joint_results = self.retrieve(query, filters=joint_filters, top_k=2)
            
        # Retrieve movement-specific knowledge
        movement_results = []
        if "movement" in focus_filters:
            movement_filters = {"movement": focus_filters["movement"]}
            movement_results = self.retrieve(query, filters=movement_filters, top_k=1)
        
        # Combine and format results
        results = general_results + joint_results + movement_results
        
        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Deduplicate
        seen_documents = set()
        unique_results = []
        for result in results:
            doc_hash = hash(result["document"][:100])  # Use first 100 chars as signature
            if doc_hash not in seen_documents:
                seen_documents.add(doc_hash)
                unique_results.append(result)
        
        # Format context
        context = "DOMAIN KNOWLEDGE CONTEXT:\n\n"
        
        for i, result in enumerate(unique_results[:5]):  # Limit to top 5
            context += f"Document {i+1} [{result['metadata'].get('type', 'general')}]:\n"
            context += f"{result['document']}\n\n"
            
        return context.strip()
    
    def _extract_focus_from_query(self, query: str, params: Dict[str, float]) -> Dict[str, str]:
        """
        Extract focus areas (joints, movements) from query and parameters.
        
        Args:
            query: Query text
            params: Current biomechanical parameters
            
        Returns:
            Dictionary with extracted focus information
        """
        focus = {}
        query_lower = query.lower()
        
        # Check for joints
        joints = {
            "knee": ["knee", "patella", "acl", "pcl", "mcl", "lcl"],
            "hip": ["hip", "pelvis", "femur"],
            "ankle": ["ankle", "foot", "tarsus", "calcaneus"],
            "shoulder": ["shoulder", "rotator cuff", "scapula", "glenohumeral"],
            "elbow": ["elbow", "forearm", "ulna", "radius"],
            "spine": ["spine", "back", "vertebra", "lumbar", "thoracic", "cervical"],
            "wrist": ["wrist", "hand", "carpus"]
        }
        
        # Check for movements
        movements = {
            "squat": ["squat", "bend", "crouch"],
            "jump": ["jump", "leap", "hop", "plyometric"],
            "run": ["run", "sprint", "jog"],
            "throw": ["throw", "pitch", "toss"],
            "lift": ["lift", "raise", "hoist", "clean", "press", "snatch"],
            "swing": ["swing", "bat", "golf", "tennis"],
            "kick": ["kick", "punt", "soccer"]
        }
        
        # Determine primary joint from query and parameters
        max_joint_score = 0
        primary_joint = None
        
        for joint, keywords in joints.items():
            # Score based on query mentions
            joint_score = sum(query_lower.count(kw) for kw in keywords)
            
            # Add score based on parameters
            joint_score += sum(1 for param in params if joint in param.lower())
            
            if joint_score > max_joint_score:
                max_joint_score = joint_score
                primary_joint = joint
        
        if primary_joint:
            focus["joint"] = primary_joint
        
        # Determine primary movement from query
        max_movement_score = 0
        primary_movement = None
        
        for movement, keywords in movements.items():
            movement_score = sum(query_lower.count(kw) for kw in keywords)
            
            if movement_score > max_movement_score:
                max_movement_score = movement_score
                primary_movement = movement
        
        if primary_movement:
            focus["movement"] = primary_movement
        
        return focus
    
    def retrieve_posture_templates(self, movement_type: str) -> List[Dict[str, Any]]:
        """
        Retrieve template postures for a specific movement type.
        
        Args:
            movement_type: Type of movement (e.g., "squat", "jump")
            
        Returns:
            List of posture templates
        """
        # Retrieve documents related to the movement
        filters = {"movement": movement_type}
        results = self.retrieve(movement_type, filters=filters, top_k=3)
        
        templates = []
        for result in results:
            # Extract posture data from documents
            document = result["document"]
            metadata = result["metadata"]
            
            # Parse any JSON or structured data in the document
            try:
                # Look for posture data in the document
                import re
                json_pattern = r'```json\s*(.*?)\s*```'
                json_matches = re.findall(json_pattern, document, re.DOTALL)
                
                for json_str in json_matches:
                    try:
                        data = json.loads(json_str)
                        if "pose_data" in data or "joint_angles" in data:
                            templates.append({
                                "data": data,
                                "metadata": metadata,
                                "similarity": result["similarity"]
                            })
                    except:
                        pass
            except:
                pass
        
        return templates
    
    def index_documents(self, documents: List[Dict[str, Any]], category: str = "user_added"):
        """
        Add new documents to the knowledge base.
        
        Args:
            documents: List of documents to add
            category: Category of the documents
        """
        if not documents:
            return
            
        # Process and add documents
        for doc in documents:
            doc["category"] = category
            self._process_document(doc, f"user_added_{len(self.documents)}")
        
        # Recompute embeddings
        self._compute_embeddings()
        
        # Save updated embeddings
        self._save_embeddings()
        
        logger.info(f"Added {len(documents)} new documents to knowledge base")
        
    def export_feedback(self, feedback: Dict[str, Any], output_path: Optional[str] = None):
        """
        Export user feedback to a file for future knowledge base improvements.
        
        Args:
            feedback: User feedback dictionary
            output_path: Optional path to save feedback
        """
        if not output_path:
            output_path = self.knowledge_base_path / "feedback.jsonl"
            
        # Append feedback to file
        with open(output_path, "a") as f:
            f.write(json.dumps(feedback) + "\n")
        
        logger.info(f"Saved user feedback to {output_path}") 