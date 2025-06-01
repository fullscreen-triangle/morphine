pub mod context;
pub mod reasoning;
pub mod intuition;
pub mod metabolic;
pub mod knowledge;

use std::sync::Arc;
use std::collections::HashMap;
use tokio::sync::{mpsc, RwLock, Mutex};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamingContext {
    pub stream_id: String,
    pub timestamp: f64,
    pub partial_data: HashMap<String, serde_json::Value>,
    pub confidence_level: f64,
    pub processing_stage: ProcessingStage,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ProcessingStage {
    Context,
    Reasoning,
    Intuition,
    Complete,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetacognitiveDecision {
    pub decision_id: String,
    pub stream_id: String,
    pub decision_type: DecisionType,
    pub confidence: f64,
    pub evidence: HashMap<String, serde_json::Value>,
    pub timestamp: f64,
    pub layer_contributions: LayerContributions,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DecisionType {
    BettingOpportunity,
    LocationVerification,
    TransactionValidation,
    StreamAnalysis,
    AlertGeneration,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LayerContributions {
    pub context_weight: f64,
    pub reasoning_weight: f64,
    pub intuition_weight: f64,
    pub metabolic_state: MetabolicState,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetabolicState {
    pub glycolytic_load: f64,
    pub lactate_level: f64,
    pub dreaming_active: bool,
    pub resource_allocation: HashMap<String, f64>,
}

pub struct MetacognitiveOrchestrator {
    // Three-layer architecture
    context_layer: Arc<context::ContextLayer>,
    reasoning_layer: Arc<reasoning::ReasoningLayer>,
    intuition_layer: Arc<intuition::IntuitionLayer>,
    
    // Metabolic components
    glycolytic_cycle: Arc<metabolic::GlycolyticCycle>,
    lactate_cycle: Arc<metabolic::LactateCycle>,
    dreaming_module: Arc<metabolic::DreamingModule>,
    
    // Knowledge management
    knowledge_base: Arc<knowledge::KnowledgeBase>,
    
    // Streaming infrastructure
    input_streams: Arc<RwLock<HashMap<String, mpsc::Receiver<StreamingContext>>>>,
    output_streams: Arc<RwLock<HashMap<String, mpsc::Sender<MetacognitiveDecision>>>>,
    
    // State management
    active_contexts: Arc<RwLock<HashMap<String, StreamingContext>>>,
    pending_decisions: Arc<RwLock<HashMap<String, MetacognitiveDecision>>>,
    processing_queue: Arc<Mutex<Vec<String>>>,
    
    // AI system integration
    ai_systems: Arc<RwLock<HashMap<String, Box<dyn AISystem + Send + Sync>>>>,
    system_weights: Arc<RwLock<HashMap<String, f64>>>,
}

#[async_trait::async_trait]
pub trait AISystem {
    async fn process(&self, context: &StreamingContext) -> Result<serde_json::Value, Box<dyn std::error::Error + Send + Sync>>;
    fn get_confidence(&self, input: &serde_json::Value) -> f64;
    fn get_system_id(&self) -> String;
    fn get_processing_time(&self) -> f64;
}

impl MetacognitiveOrchestrator {
    pub async fn new() -> Self {
        Self {
            context_layer: Arc::new(context::ContextLayer::new().await),
            reasoning_layer: Arc::new(reasoning::ReasoningLayer::new().await),
            intuition_layer: Arc::new(intuition::IntuitionLayer::new().await),
            
            glycolytic_cycle: Arc::new(metabolic::GlycolyticCycle::new()),
            lactate_cycle: Arc::new(metabolic::LactateCycle::new()),
            dreaming_module: Arc::new(metabolic::DreamingModule::new()),
            
            knowledge_base: Arc::new(knowledge::KnowledgeBase::new().await),
            
            input_streams: Arc::new(RwLock::new(HashMap::new())),
            output_streams: Arc::new(RwLock::new(HashMap::new())),
            
            active_contexts: Arc::new(RwLock::new(HashMap::new())),
            pending_decisions: Arc::new(RwLock::new(HashMap::new())),
            processing_queue: Arc::new(Mutex::new(Vec::new())),
            
            ai_systems: Arc::new(RwLock::new(HashMap::new())),
            system_weights: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    pub async fn register_ai_system(
        &self, 
        system: Box<dyn AISystem + Send + Sync>,
        weight: f64
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let system_id = system.get_system_id();
        
        {
            let mut ai_systems = self.ai_systems.write().await;
            ai_systems.insert(system_id.clone(), system);
        }
        
        {
            let mut weights = self.system_weights.write().await;
            weights.insert(system_id, weight);
        }
        
        Ok(())
    }
    
    pub async fn create_stream(&self, stream_id: String) -> (mpsc::Sender<StreamingContext>, mpsc::Receiver<MetacognitiveDecision>) {
        let (input_tx, input_rx) = mpsc::channel(1000);
        let (output_tx, output_rx) = mpsc::channel(1000);
        
        {
            let mut input_streams = self.input_streams.write().await;
            input_streams.insert(stream_id.clone(), input_rx);
        }
        
        {
            let mut output_streams = self.output_streams.write().await;
            output_streams.insert(stream_id.clone(), output_tx);
        }
        
        // Start processing loop for this stream
        let orchestrator = self.clone();
        tokio::spawn(async move {
            orchestrator.process_stream(stream_id).await;
        });
        
        (input_tx, output_rx)
    }
    
    async fn process_stream(&self, stream_id: String) {
        let mut input_rx = {
            let mut input_streams = self.input_streams.write().await;
            input_streams.remove(&stream_id).unwrap()
        };
        
        while let Some(context) = input_rx.recv().await {
            // Store active context
            {
                let mut active_contexts = self.active_contexts.write().await;
                active_contexts.insert(context.stream_id.clone(), context.clone());
            }
            
            // Process through metacognitive layers
            let decision = self.process_context(context).await;
            
            // Send decision if we have an output stream
            if let Ok(output_streams) = self.output_streams.read().await {
                if let Some(output_tx) = output_streams.get(&stream_id) {
                    let _ = output_tx.send(decision).await;
                }
            }
        }
    }
    
    async fn process_context(&self, mut context: StreamingContext) -> MetacognitiveDecision {
        let decision_id = Uuid::new_v4().to_string();
        
        // Check metabolic state and allocate resources
        let metabolic_state = self.assess_metabolic_state(&context).await;
        let resource_allocation = self.glycolytic_cycle.allocate_resources(&context, &metabolic_state).await;
        
        // Process through three layers concurrently with streaming
        let (context_result, reasoning_result, intuition_result) = tokio::join!(
            self.process_context_layer(&context),
            self.process_reasoning_layer(&context),
            self.process_intuition_layer(&context)
        );
        
        // Combine layer outputs with dynamic weighting
        let layer_contributions = self.calculate_layer_weights(
            &context_result,
            &reasoning_result, 
            &intuition_result,
            &metabolic_state
        ).await;
        
        // Generate decision with evidence fusion
        let decision = self.synthesize_decision(
            decision_id,
            context,
            context_result,
            reasoning_result,
            intuition_result,
            layer_contributions,
            metabolic_state
        ).await;
        
        // Store in lactate cycle if incomplete
        if decision.confidence < 0.8 {
            self.lactate_cycle.store_partial_result(&decision).await;
        }
        
        // Update dreaming module with new patterns
        self.dreaming_module.incorporate_experience(&decision).await;
        
        decision
    }
    
    async fn process_context_layer(&self, context: &StreamingContext) -> serde_json::Value {
        // Parallel processing of all AI systems for context understanding
        let ai_systems = self.ai_systems.read().await;
        let mut context_results = HashMap::new();
        
        for (system_id, system) in ai_systems.iter() {
            if let Ok(result) = system.process(context).await {
                context_results.insert(system_id.clone(), result);
            }
        }
        
        // Context layer processing with knowledge integration
        self.context_layer.process(context, &context_results, &self.knowledge_base).await
    }
    
    async fn process_reasoning_layer(&self, context: &StreamingContext) -> serde_json::Value {
        // Rule-based inference with causal reasoning
        self.reasoning_layer.process(context, &self.knowledge_base).await
    }
    
    async fn process_intuition_layer(&self, context: &StreamingContext) -> serde_json::Value {
        // Pattern recognition and predictive modeling
        self.intuition_layer.process(context, &self.knowledge_base).await
    }
    
    async fn assess_metabolic_state(&self, context: &StreamingContext) -> MetabolicState {
        let glycolytic_load = self.glycolytic_cycle.get_current_load().await;
        let lactate_level = self.lactate_cycle.get_lactate_level().await;
        let dreaming_active = self.dreaming_module.is_active().await;
        let resource_allocation = self.glycolytic_cycle.get_resource_allocation().await;
        
        MetabolicState {
            glycolytic_load,
            lactate_level,
            dreaming_active,
            resource_allocation,
        }
    }
    
    async fn calculate_layer_weights(
        &self,
        context_result: &serde_json::Value,
        reasoning_result: &serde_json::Value,
        intuition_result: &serde_json::Value,
        metabolic_state: &MetabolicState
    ) -> LayerContributions {
        // Dynamic weight calculation based on confidence and metabolic state
        let context_confidence = self.extract_confidence(context_result);
        let reasoning_confidence = self.extract_confidence(reasoning_result);
        let intuition_confidence = self.extract_confidence(intuition_result);
        
        let total_confidence = context_confidence + reasoning_confidence + intuition_confidence;
        
        LayerContributions {
            context_weight: context_confidence / total_confidence,
            reasoning_weight: reasoning_confidence / total_confidence,
            intuition_weight: intuition_confidence / total_confidence,
            metabolic_state: metabolic_state.clone(),
        }
    }
    
    async fn synthesize_decision(
        &self,
        decision_id: String,
        context: StreamingContext,
        context_result: serde_json::Value,
        reasoning_result: serde_json::Value,
        intuition_result: serde_json::Value,
        layer_contributions: LayerContributions,
        metabolic_state: MetabolicState
    ) -> MetacognitiveDecision {
        let mut evidence = HashMap::new();
        evidence.insert("context".to_string(), context_result);
        evidence.insert("reasoning".to_string(), reasoning_result);
        evidence.insert("intuition".to_string(), intuition_result);
        
        // Determine decision type based on context and evidence
        let decision_type = self.classify_decision_type(&context, &evidence).await;
        
        // Calculate overall confidence using weighted evidence
        let confidence = self.calculate_overall_confidence(&evidence, &layer_contributions).await;
        
        MetacognitiveDecision {
            decision_id,
            stream_id: context.stream_id,
            decision_type,
            confidence,
            evidence,
            timestamp: context.timestamp,
            layer_contributions,
        }
    }
    
    async fn classify_decision_type(&self, context: &StreamingContext, evidence: &HashMap<String, serde_json::Value>) -> DecisionType {
        // Implement sophisticated decision type classification
        // This would use the reasoning layer and pattern matching
        DecisionType::StreamAnalysis // Placeholder
    }
    
    async fn calculate_overall_confidence(&self, evidence: &HashMap<String, serde_json::Value>, contributions: &LayerContributions) -> f64 {
        // Weighted confidence calculation based on layer contributions
        let context_conf = self.extract_confidence(evidence.get("context").unwrap());
        let reasoning_conf = self.extract_confidence(evidence.get("reasoning").unwrap());
        let intuition_conf = self.extract_confidence(evidence.get("intuition").unwrap());
        
        (context_conf * contributions.context_weight +
         reasoning_conf * contributions.reasoning_weight +
         intuition_conf * contributions.intuition_weight)
    }
    
    fn extract_confidence(&self, result: &serde_json::Value) -> f64 {
        result.get("confidence")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.5)
    }
    
    pub async fn get_streaming_decisions(&self, stream_id: &str) -> Vec<MetacognitiveDecision> {
        // Return decisions as they become available, not waiting for complete processing
        let pending = self.pending_decisions.read().await;
        pending.values()
            .filter(|d| d.stream_id == stream_id)
            .cloned()
            .collect()
    }
    
    pub async fn get_system_health(&self) -> HashMap<String, serde_json::Value> {
        let mut health = HashMap::new();
        
        // Metabolic health
        let metabolic_state = MetabolicState {
            glycolytic_load: self.glycolytic_cycle.get_current_load().await,
            lactate_level: self.lactate_cycle.get_lactate_level().await,
            dreaming_active: self.dreaming_module.is_active().await,
            resource_allocation: self.glycolytic_cycle.get_resource_allocation().await,
        };
        
        health.insert("metabolic_state".to_string(), serde_json::to_value(metabolic_state).unwrap());
        health.insert("active_streams".to_string(), serde_json::Value::Number(
            self.active_contexts.read().await.len().into()
        ));
        
        // AI system status
        let ai_systems = self.ai_systems.read().await;
        health.insert("registered_ai_systems".to_string(), serde_json::Value::Number(
            ai_systems.len().into()
        ));
        
        health
    }
}

impl Clone for MetacognitiveOrchestrator {
    fn clone(&self) -> Self {
        Self {
            context_layer: self.context_layer.clone(),
            reasoning_layer: self.reasoning_layer.clone(),
            intuition_layer: self.intuition_layer.clone(),
            glycolytic_cycle: self.glycolytic_cycle.clone(),
            lactate_cycle: self.lactate_cycle.clone(),
            dreaming_module: self.dreaming_module.clone(),
            knowledge_base: self.knowledge_base.clone(),
            input_streams: self.input_streams.clone(),
            output_streams: self.output_streams.clone(),
            active_contexts: self.active_contexts.clone(),
            pending_decisions: self.pending_decisions.clone(),
            processing_queue: self.processing_queue.clone(),
            ai_systems: self.ai_systems.clone(),
            system_weights: self.system_weights.clone(),
        }
    }
} 