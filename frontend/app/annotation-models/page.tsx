'use client';

import React, { useState, useEffect } from 'react';

interface AnnotationModel {
  modelId: string;
  title: string;
  expert: string;
  category: string;
  expertise: string;
  knowledgeDepth: string;
  price: number;
  totalApplications: number;
  avgRating: number;
  applicableVideoTypes: string[];
}

interface VideoContent {
  id: string;
  title: string;
  category: string;
  duration: string;
  thumbnail: string;
  compatibleModels: number;
}

export default function AnnotationModelsPage() {
  const [activeTab, setActiveTab] = useState('discover');
  const [selectedVideo, setSelectedVideo] = useState<VideoContent | null>(null);
  const [availableModels, setAvailableModels] = useState<AnnotationModel[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [isExpertMode, setIsExpertMode] = useState(false);

  const sampleVideos: VideoContent[] = [
    {
      id: 'video_1',
      title: 'Beautiful Garden Tour - Spring Flowers',
      category: 'flowers',
      duration: '15:30',
      thumbnail: '🌸',
      compatibleModels: 12
    },
    {
      id: 'video_2', 
      title: 'Gordon Ramsay Cooking Masterclass',
      category: 'cooking',
      duration: '45:20',
      thumbnail: '🍳',
      compatibleModels: 23
    },
    {
      id: 'video_3',
      title: 'Modern Architecture Documentary',
      category: 'architecture', 
      duration: '1:20:15',
      thumbnail: '🏢',
      compatibleModels: 8
    },
    {
      id: 'video_4',
      title: 'Brain Surgery Live Stream',
      category: 'medical',
      duration: '3:45:00',
      thumbnail: '🧠',
      compatibleModels: 15
    },
    {
      id: 'video_5',
      title: 'NBA Finals Game 7',
      category: 'sports',
      duration: '2:30:00',
      thumbnail: '🏀',
      compatibleModels: 31
    }
  ];

  const sampleModels: AnnotationModel[] = [
    {
      modelId: 'model_1',
      title: 'Master Botanist Flower Identification',
      expert: 'Dr. Sarah Green',
      category: 'flowers',
      expertise: 'Botanical Science',
      knowledgeDepth: 'master',
      price: 2.50,
      totalApplications: 15420,
      avgRating: 4.9,
      applicableVideoTypes: ['garden tours', 'nature documentaries', 'flower arrangement']
    },
    {
      modelId: 'model_2',
      title: 'Professional Chef Technique Analysis',
      expert: 'Chef Marcus Williams',
      category: 'cooking',
      expertise: 'Culinary Arts',
      knowledgeDepth: 'expert',
      price: 3.00,
      totalApplications: 28750,
      avgRating: 4.8,
      applicableVideoTypes: ['cooking shows', 'recipe videos', 'kitchen techniques']
    },
    {
      modelId: 'model_3',
      title: 'Structural Engineering Insights',
      expert: 'Frank Lloyd Wright Jr.',
      category: 'architecture',
      expertise: 'Structural Engineering',
      knowledgeDepth: 'master',
      price: 5.00,
      totalApplications: 8930,
      avgRating: 4.95,
      applicableVideoTypes: ['building tours', 'construction videos', 'design presentations']
    },
    {
      modelId: 'model_4',
      title: 'Neurosurgeon Medical Commentary',
      expert: 'Dr. Emily Chen',
      category: 'medical',
      expertise: 'Neurosurgery',
      knowledgeDepth: 'master',
      price: 8.00,
      totalApplications: 5240,
      avgRating: 4.97,
      applicableVideoTypes: ['surgery streams', 'medical education', 'patient care']
    },
    {
      modelId: 'model_5',
      title: 'Basketball Analytics Expert',
      expert: 'Coach Mike Johnson',
      category: 'sports',
      expertise: 'Basketball Strategy',
      knowledgeDepth: 'expert',
      price: 1.50,
      totalApplications: 45600,
      avgRating: 4.7,
      applicableVideoTypes: ['basketball games', 'player analysis', 'strategy breakdowns']
    }
  ];

  useEffect(() => {
    if (selectedVideo) {
      // Filter models compatible with selected video
      const compatible = sampleModels.filter(model => 
        model.category === selectedVideo.category ||
        model.applicableVideoTypes.some(type => 
          selectedVideo.title.toLowerCase().includes(type.split(' ')[0])
        )
      );
      setAvailableModels(compatible);
    }
  }, [selectedVideo]);

  const handleVideoSelect = (video: VideoContent) => {
    setSelectedVideo(video);
    setSelectedModels([]);
  };

  const handleModelSelect = (modelId: string) => {
    if (selectedModels.includes(modelId)) {
      setSelectedModels(selectedModels.filter(id => id !== modelId));
    } else {
      setSelectedModels([...selectedModels, modelId]);
    }
  };

  const calculateTotalCost = () => {
    return selectedModels.reduce((total, modelId) => {
      const model = availableModels.find(m => m.modelId === modelId);
      return total + (model?.price || 0);
    }, 0);
  };

  const getKnowledgeDepthColor = (depth: string) => {
    const colors = {
      beginner: 'text-green-400',
      intermediate: 'text-yellow-400', 
      expert: 'text-orange-400',
      master: 'text-red-400'
    };
    return colors[depth as keyof typeof colors] || 'text-gray-400';
  };

  const getKnowledgeDepthIcon = (depth: string) => {
    const icons = {
      beginner: '🌱',
      intermediate: '🌿',
      expert: '🌳',
      master: '🏆'
    };
    return icons[depth as keyof typeof icons] || '📚';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 text-white">
      {/* Header */}
      <div className="bg-black/20 backdrop-blur-sm border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-yellow-400 to-orange-500 bg-clip-text text-transparent">
              Universal Annotation Models
            </h1>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setIsExpertMode(!isExpertMode)}
                className={`px-4 py-2 rounded-lg transition-all ${
                  isExpertMode 
                    ? 'bg-green-600 text-white' 
                    : 'bg-white/10 hover:bg-white/20'
                }`}
              >
                {isExpertMode ? '🧠 Expert Mode ON' : '👤 Switch to Expert Mode'}
              </button>
            </div>
          </div>
          <p className="text-lg opacity-80 mt-2">
            Apply expert knowledge to any video content • Create models once, enhance unlimited videos
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Tab Navigation */}
        <div className="flex space-x-4 mb-8">
          <button
            onClick={() => setActiveTab('discover')}
            className={`px-6 py-3 rounded-lg font-bold transition-all ${
              activeTab === 'discover'
                ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white'
                : 'bg-white/10 hover:bg-white/20'
            }`}
          >
            🔍 Discover Models
          </button>
          <button
            onClick={() => setActiveTab('create')}
            className={`px-6 py-3 rounded-lg font-bold transition-all ${
              activeTab === 'create'
                ? 'bg-gradient-to-r from-green-600 to-blue-600 text-white'
                : 'bg-white/10 hover:bg-white/20'
            }`}
          >
            ✨ Create Model
          </button>
          <button
            onClick={() => setActiveTab('marketplace')}
            className={`px-6 py-3 rounded-lg font-bold transition-all ${
              activeTab === 'marketplace'
                ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white'
                : 'bg-white/10 hover:bg-white/20'
            }`}
          >
            🏪 Marketplace
          </button>
          <button
            onClick={() => setActiveTab('earnings')}
            className={`px-6 py-3 rounded-lg font-bold transition-all ${
              activeTab === 'earnings'
                ? 'bg-gradient-to-r from-yellow-600 to-orange-600 text-white'
                : 'bg-white/10 hover:bg-white/20'
            }`}
          >
            💰 Earnings
          </button>
        </div>

        {/* Discover Models Tab */}
        {activeTab === 'discover' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Video Selection */}
            <div className="lg:col-span-1">
              <div className="bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10">
                <h3 className="text-xl font-bold mb-4">🎬 Select Video Content</h3>
                <div className="space-y-3">
                  {sampleVideos.map((video) => (
                    <button
                      key={video.id}
                      onClick={() => handleVideoSelect(video)}
                      className={`w-full p-4 rounded-lg transition-all text-left ${
                        selectedVideo?.id === video.id
                          ? 'bg-gradient-to-r from-blue-600 to-purple-600 transform scale-105'
                          : 'bg-white/10 hover:bg-white/20'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <span className="text-3xl">{video.thumbnail}</span>
                        <div className="flex-1">
                          <div className="font-bold text-sm">{video.title}</div>
                          <div className="text-xs opacity-70">
                            {video.duration} • {video.compatibleModels} compatible models
                          </div>
                          <div className="text-xs text-yellow-400 capitalize">
                            {video.category}
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>

                {selectedVideo && (
                  <div className="mt-6 p-4 bg-blue-600/20 rounded-lg border border-blue-400/30">
                    <h4 className="font-bold text-blue-400 mb-2">🎯 Selected Video</h4>
                    <p className="text-sm">{selectedVideo.title}</p>
                    <p className="text-xs opacity-70 mt-1">
                      {availableModels.length} expert models can enhance this video
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Compatible Models */}
            <div className="lg:col-span-2">
              {selectedVideo ? (
                <div className="bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10">
                  <h3 className="text-xl font-bold mb-4">
                    🧠 Compatible Expert Models for "{selectedVideo.title}"
                  </h3>
                  
                  <div className="grid gap-4 mb-6">
                    {availableModels.map((model) => (
                      <div
                        key={model.modelId}
                        className={`p-4 rounded-lg border transition-all cursor-pointer ${
                          selectedModels.includes(model.modelId)
                            ? 'bg-green-600/20 border-green-400'
                            : 'bg-white/10 border-white/20 hover:bg-white/20'
                        }`}
                        onClick={() => handleModelSelect(model.modelId)}
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-2">
                              <span className={getKnowledgeDepthColor(model.knowledgeDepth)}>
                                {getKnowledgeDepthIcon(model.knowledgeDepth)}
                              </span>
                              <h4 className="font-bold">{model.title}</h4>
                            </div>
                            <p className="text-sm opacity-80 mb-2">
                              Expert: {model.expert} • {model.expertise}
                            </p>
                            <div className="flex items-center space-x-4 text-xs">
                              <span className="text-yellow-400">
                                ⭐ {model.avgRating}/5.0
                              </span>
                              <span className="text-blue-400">
                                📊 {model.totalApplications.toLocaleString()} applications
                              </span>
                              <span className={getKnowledgeDepthColor(model.knowledgeDepth)}>
                                🎓 {model.knowledgeDepth}
                              </span>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-lg font-bold text-green-400">
                              ${model.price}
                            </div>
                            <div className="text-xs opacity-70">per application</div>
                          </div>
                        </div>
                        
                        <div className="mt-3 flex flex-wrap gap-1">
                          {model.applicableVideoTypes.slice(0, 3).map((type, index) => (
                            <span
                              key={index}
                              className="px-2 py-1 bg-purple-600/30 rounded text-xs"
                            >
                              {type}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>

                  {selectedModels.length > 0 && (
                    <div className="bg-gradient-to-r from-green-600/20 to-blue-600/20 rounded-lg p-4 border border-green-400/30">
                      <div className="flex justify-between items-center">
                        <div>
                          <h4 className="font-bold text-green-400">
                            🎯 {selectedModels.length} Models Selected
                          </h4>
                          <p className="text-sm opacity-80">
                            Your video will be enhanced with expert knowledge from {selectedModels.length} specialists
                          </p>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-green-400">
                            ${calculateTotalCost().toFixed(2)}
                          </div>
                          <button className="mt-2 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-500 hover:to-blue-500 px-6 py-2 rounded-lg font-bold transition-all">
                            Apply Models
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10 flex items-center justify-center h-96">
                  <div className="text-center">
                    <div className="text-6xl mb-4">🎬</div>
                    <h3 className="text-xl font-bold mb-2">Select a Video to Begin</h3>
                    <p className="text-sm opacity-70">
                      Choose any video content to discover compatible expert annotation models
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Create Model Tab */}
        {activeTab === 'create' && (
          <div className="bg-black/30 backdrop-blur-sm rounded-xl p-8 border border-white/10">
            <h2 className="text-2xl font-bold mb-6">✨ Create Your Universal Annotation Model</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <h3 className="text-lg font-bold mb-4">📝 Model Information</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-bold mb-2">Model Title</label>
                    <input
                      type="text"
                      placeholder="e.g., Master Gardener's Flower Identification Guide"
                      className="w-full p-3 bg-white/10 border border-white/20 rounded-lg"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-bold mb-2" htmlFor="category-select">Category</label>
                    <select 
                      id="category-select"
                      title="Select video category"
                      className="w-full p-3 bg-white/10 border border-white/20 rounded-lg"
                    >
                      <option value="">Select Category</option>
                      <option value="flowers">🌸 Flowers & Botany</option>
                      <option value="cooking">🍳 Cooking & Culinary</option>
                      <option value="architecture">🏢 Architecture & Construction</option>
                      <option value="medical">🏥 Medical & Healthcare</option>
                      <option value="sports">⚽ Sports & Athletics</option>
                      <option value="education">🎓 Education & Learning</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-bold mb-2">Your Expertise</label>
                    <input
                      type="text"
                      placeholder="e.g., 20 years professional gardening experience"
                      className="w-full p-3 bg-white/10 border border-white/20 rounded-lg"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-bold mb-2" htmlFor="knowledge-depth-select">Knowledge Depth</label>
                    <select 
                      id="knowledge-depth-select"
                      title="Select your knowledge depth level"
                      className="w-full p-3 bg-white/10 border border-white/20 rounded-lg"
                    >
                      <option value="beginner">🌱 Beginner - Basic insights</option>
                      <option value="intermediate">🌿 Intermediate - Practical knowledge</option>
                      <option value="expert">🌳 Expert - Professional level</option>
                      <option value="master">🏆 Master - World-class expertise</option>
                    </select>
                  </div>
                </div>
              </div>
              
              <div>
                <h3 className="text-lg font-bold mb-4">💰 Monetization</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-bold mb-2">Price per Application</label>
                    <div className="flex items-center space-x-2">
                      <span className="text-green-400">$</span>
                      <input
                        type="number"
                        placeholder="2.50"
                        step="0.25"
                        min="0.25"
                        className="flex-1 p-3 bg-white/10 border border-white/20 rounded-lg"
                      />
                    </div>
                    <p className="text-xs opacity-70 mt-1">
                      Earn every time someone applies your model to a video
                    </p>
                  </div>
                  
                  <div className="bg-green-600/20 rounded-lg p-4 border border-green-400/30">
                    <h4 className="font-bold text-green-400 mb-2">💡 Earning Potential</h4>
                    <div className="text-sm space-y-1">
                      <div>Daily: $125 - $500</div>
                      <div>Monthly: $3,750 - $15,000</div>
                      <div>Yearly: $45,000 - $180,000</div>
                    </div>
                    <p className="text-xs opacity-80 mt-2">
                      Based on average application rates for expert models
                    </p>
                  </div>
                  
                  <div className="bg-purple-600/20 rounded-lg p-4 border border-purple-400/30">
                    <h4 className="font-bold text-purple-400 mb-2">🚀 Revolutionary Impact</h4>
                    <ul className="text-sm space-y-1">
                      <li>• Your expertise enhances unlimited videos</li>
                      <li>• Passive income from knowledge created once</li>
                      <li>• Global reach to millions of learners</li>
                      <li>• Knowledge becomes immortal digital asset</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="mt-8 text-center">
              <button className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 px-8 py-3 rounded-lg font-bold text-lg transition-all">
                🚀 Create Universal Model
              </button>
              <p className="text-sm opacity-70 mt-2">
                Your expertise will be available to enhance any compatible video content globally
              </p>
            </div>
          </div>
        )}

        {/* Marketplace Tab */}
        {activeTab === 'marketplace' && (
          <div className="space-y-6">
            {/* Marketplace Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-xl p-4 border border-blue-400/30">
                <div className="text-2xl font-bold text-blue-400">2,847</div>
                <div className="text-sm opacity-80">Total Models</div>
              </div>
              <div className="bg-gradient-to-r from-green-600/20 to-blue-600/20 rounded-xl p-4 border border-green-400/30">
                <div className="text-2xl font-bold text-green-400">1,234</div>
                <div className="text-sm opacity-80">Expert Creators</div>
              </div>
              <div className="bg-gradient-to-r from-yellow-600/20 to-orange-600/20 rounded-xl p-4 border border-yellow-400/30">
                <div className="text-2xl font-bold text-yellow-400">45M</div>
                <div className="text-sm opacity-80">Videos Enhanced</div>
              </div>
              <div className="bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-xl p-4 border border-purple-400/30">
                <div className="text-2xl font-bold text-purple-400">$2.8M</div>
                <div className="text-sm opacity-80">Expert Earnings</div>
              </div>
            </div>

            {/* Featured Models */}
            <div className="bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10">
              <h3 className="text-xl font-bold mb-4">🏆 Featured Expert Models</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sampleModels.map((model) => (
                  <div key={model.modelId} className="bg-white/10 rounded-lg p-4 border border-white/20">
                    <div className="flex items-center space-x-2 mb-2">
                      <span className={getKnowledgeDepthColor(model.knowledgeDepth)}>
                        {getKnowledgeDepthIcon(model.knowledgeDepth)}
                      </span>
                      <h4 className="font-bold text-sm">{model.title}</h4>
                    </div>
                    <p className="text-xs opacity-80 mb-2">by {model.expert}</p>
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-yellow-400 text-sm">⭐ {model.avgRating}</span>
                      <span className="text-green-400 font-bold">${model.price}</span>
                    </div>
                    <div className="text-xs opacity-70 mb-3">
                      {model.totalApplications.toLocaleString()} applications
                    </div>
                    <button className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 py-2 rounded text-sm font-bold transition-all">
                      View Model
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Earnings Tab */}
        {activeTab === 'earnings' && (
          <div className="space-y-6">
            <div className="bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10">
              <h2 className="text-2xl font-bold mb-6">💰 Expert Earnings Dashboard</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-gradient-to-r from-green-600/20 to-blue-600/20 rounded-lg p-4">
                  <h3 className="font-bold text-green-400 mb-2">🎯 Active Models</h3>
                  <div className="text-2xl font-bold">5</div>
                  <div className="text-sm opacity-70">Generating revenue</div>
                </div>
                
                <div className="bg-gradient-to-r from-yellow-600/20 to-orange-600/20 rounded-lg p-4">
                  <h3 className="font-bold text-yellow-400 mb-2">📊 Total Applications</h3>
                  <div className="text-2xl font-bold">12,847</div>
                  <div className="text-sm opacity-70">Across all models</div>
                </div>
                
                <div className="bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-lg p-4">
                  <h3 className="font-bold text-purple-400 mb-2">💸 Total Earnings</h3>
                  <div className="text-2xl font-bold">$24,350</div>
                  <div className="text-sm opacity-70">Lifetime revenue</div>
                </div>
              </div>
              
              <div className="mt-8 bg-white/10 rounded-lg p-6">
                <h3 className="text-lg font-bold mb-4">🚀 Revolutionary Passive Income</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-bold mb-2">Your Knowledge Assets:</h4>
                    <ul className="text-sm space-y-1 opacity-80">
                      <li>• Flower identification expertise → 3,420 applications</li>
                      <li>• Garden design principles → 2,890 applications</li>
                      <li>• Plant care techniques → 4,150 applications</li>
                      <li>• Botanical photography → 1,720 applications</li>
                      <li>• Seasonal gardening → 667 applications</li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-bold mb-2">Infinite Scalability:</h4>
                    <ul className="text-sm space-y-1 opacity-80">
                      <li>• Your models enhance unlimited videos</li>
                      <li>• Zero additional time investment required</li>
                      <li>• Global reach to millions of learners</li>
                      <li>• Knowledge preserved forever as digital assets</li>
                      <li>• Earnings continue indefinitely</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 