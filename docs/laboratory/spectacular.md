<h1 align="center">Spectacular</h1>
<p align="center"><em> The eye never has enough of seeing, nor the ear its fill of hearing</em></p>

<p align="center">
  <img src="./spectacular.png" alt="Spectacular Logo" width="300"/>
</p>

![version](https://img.shields.io/badge/version-0.1.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)

> An interactive biomechanical knowledge platform combining 3D visualization, natural language conversation, and domain-specific AI.

## Overview

Spectacular bridges the gap between complex biomechanical knowledge and intuitive understanding by creating an interactive system where users can:

1. Explore 3D models of human anatomy with direct pointing/clicking
2. Engage in natural language conversation about biomechanics
3. Visualize movements and postures through AI-driven animation

Rather than requiring users to describe anatomical structures using technical terminology, Spectacular allows them to simply click on body parts and ask questions naturally. The system provides context-aware responses and visual demonstrations, making biomechanical knowledge accessible to everyone from athletes to physical therapists to casual learners.

## Core Features

- **Interactive 3D Human Model**: Click directly on bones, muscles, and joints
- **Contextual AI Chat**: Ask questions about the selected body parts
- **Motion Visualization**: See proper movements demonstrated in 3D
- **Biomechanical Analysis**: Upload videos for technique comparison and feedback
- **Progressive Learning**: Conversation builds on previous interactions for deeper understanding
- **AI-Powered Pose Estimation**: 2D and 3D pose tracking with advanced Hugging Face models
- **Multi-modal Analysis**: Combined skeleton-based and RGB-based action recognition
- **Voice Interaction**: Speech-to-text and text-to-speech with voice cloning capabilities

## Project Structure

```
spectacular/
├── backend/                      # Python backend
│   ├── api/                      # API endpoints
│   ├── core/                     # Core biomechanical analysis
│   │   ├── pose_pipeline.py      # 2D pose estimation
│   │   ├── pose3d.py             # 3D pose lifting
│   │   ├── video_feat.py         # Video feature extraction
│   │   ├── action_head.py        # Skeleton action classification
│   │   └── action_rgb.py         # RGB-based action recognition
│   ├── llm/                      # Domain-specific LLM integration
│   │   ├── model.py              # LLM processor (Mistral/Llama)
│   │   └── embeddings.py         # Retrieval embeddings for RAG
│   ├── voice/                    # Voice processing
│   │   ├── asr.py                # Speech recognition
│   │   └── tts.py                # Text-to-speech with voice cloning
│   ├── vision/                   # Vision processing
│   │   └── caption.py            # Frame captioning for LLM context
│   ├── utils/                    # Utilities
│   └── main.py                   # Entry point
│
├── frontend/                     # React/TypeScript frontend
│   ├── components/               # React components
│   │   ├── ModelViewer/          # 3D visualization 
│   │   ├── ChatInterface/        # Conversation UI
│   │   └── common/               # Shared components
│   ├── hooks/                    # Custom React hooks
│   └── services/                 # API clients
│
├── models/                       # Pre-trained models
│   ├── biomech_llm/              # Biomechanical LLM
│   └── pose_models/              # Pose estimation models
│
└── scripts/                      # Utility scripts
```

## Current Status

Spectacular is under active development with the following components:

- ✅ Domain-specific biomechanical LLM (based on Mistral 7B)
- ✅ Hugging Face model integration for pose estimation, action recognition and more
- ⏳ React-based 3D visualization package (partially complete)
- 🔄 Integration middleware (in planning)
- 🔄 Conversational interface (in design phase)

### Implemented Hugging Face Models

- **2D Pose Estimation**: `ultralytics/yolov8s-pose` and `qualcomm/RTMPose_Body2d`
- **3D Pose & Motion**: `walterzhu/MotionBERT-Lite` and `Tonic/video-swin-transformer`
- **Action Recognition**: Custom classifiers on MotionBERT embeddings and Video Swin
- **Retrieval (RAG)**: `sentence-transformers/all-MiniLM-L6-v2` and `scibert_scivocab_uncased`
- **Voice Processing**: `openai/whisper-large-v3` (ASR) and `coqui/XTTS-v2` (TTS)
- **Vision-Language**: `Salesforce/blip2-flan-t5-xl` for auto-captioning
- **LLM**: Base Mistral-7B with `meta-llama/Meta-Llama-3-8B-Instruct` upgrade option

The system currently consists of two main modules that need integration:
1. A Python project for domain construction and biomechanical LLM training
2. A React/TSX package for 3D posture/pose visualization

## Getting Started

### Prerequisites

- Node.js (16+)
- Python (3.9+)
- GPU with CUDA support (recommended for LLM inference)

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/spectacular.git
   cd spectacular
   ```

2. Install backend dependencies
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Install frontend dependencies
   ```bash
   cd ../frontend
   npm install
   ```

4. Download pre-trained models (optional - large files)
   ```bash
   ./scripts/download_models.sh
   ```

### Running in Development Mode

1. Start the backend
   ```bash
   cd backend
   python main.py
   ```

2. Start the frontend
   ```bash
   cd frontend
   npm run dev
   ```

3. Open your browser at http://localhost:3000

## Usage Examples

### Scenario 1: Exploring Joint Mechanics

1. View the 3D human model and click on a knee joint
2. The system highlights the joint and displays basic information
3. Ask: "What movements are possible here?"
4. The system explains and demonstrates flexion/extension movements
5. Ask: "What muscles are involved in extending this joint?"
6. The system highlights relevant muscles and explains their function

### Scenario 2: Analyzing Movement Technique

1. Select "Sprint Running" from the movement library
2. The system displays the movement pattern in the 3D model
3. Ask: "What's happening in the acceleration phase?"
4. The system explains and highlights key biomechanical elements
5. Upload your own video for comparison
6. Receive AI-powered feedback on technique differences

## Roadmap

- **Phase 1**: Core Infrastructure (in progress)
  - Basic 3D model with clickable parts
  - Simple chat interface connected to biomechanical LLM
  - Initial integration between components

- **Phase 2**: Integration & Context
  - Context-aware conversations about selected anatomy
  - Enhanced visualization with detailed anatomical structures
  - Movement sequence generation

- **Phase 3**: Advanced Features
  - Comparison tools for technique analysis
  - User data upload and processing
  - Enhanced movement visualization

## Technologies

- **Frontend**: React, TypeScript, Three.js, React Three Fiber
- **Backend**: Python, FastAPI
- **AI**: Custom biomechanical LLM (Mistral 7B) with Llama-3 upgrade option
- **Computer Vision**: YOLOv8, MotionBERT, Video Swin Transformer
- **Voice**: Whisper (ASR) and XTTS-v2 (TTS)
- **3D**: Custom motion visualization library
- **Embeddings**: Sentence-transformers and FAISS for retrieval

## Contributing

Contributions are welcome! Please check out our [Contributing Guide](CONTRIBUTING.md) for details on how to get started.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- Max Planck Institute for their motion capture datasets
- Mistral AI for the base LLM architecture
- The biomechanics research community for domain knowledge
- Hugging Face for providing the powerful AI models used in this project
