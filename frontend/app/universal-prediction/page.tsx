'use client';

import React, { useState, useEffect } from 'react';

interface StreamAnalytics {
  viewerCount: number;
  activePredictions: number;
  expertParticipation: number;
  familyGroups: number;
  retiredExperts: number;
}

interface FamilyGroup {
  id: string;
  members: string[];
  sharedSpecialist: string | null;
  predictions: any[];
  collaborativeScore: number;
}

interface PredictionCluster {
  id: string;
  type: string;
  industry: string;
  participants: number;
  specialist: string | null;
}

export default function UniversalPredictionPage() {
  const [activeIndustry, setActiveIndustry] = useState('construction');
  const [selectedSpecialist, setSelectedSpecialist] = useState<string | null>(null);
  const [familyGroup, setFamilyGroup] = useState<FamilyGroup | null>(null);
  const [predictionClusters, setPredictionClusters] = useState<PredictionCluster[]>([]);
  const [retirementMode, setRetirementMode] = useState(false);
  const [streamAnalytics, setStreamAnalytics] = useState<StreamAnalytics>({
    viewerCount: 0,
    activePredictions: 0,
    expertParticipation: 0,
    familyGroups: 0,
    retiredExperts: 0
  });

  const industries = [
    { 
      id: 'construction', 
      name: 'Construction', 
      icon: '🏗️',
      liveStreams: ['Road Construction Project Alpha', 'Building Site Live Cam', 'Heavy Machinery Operations'],
      specialists: ['40-Year Road Expert', 'Safety Prediction Pro', 'Equipment Failure Predictor'],
      retiredExperts: 456,
      avgIncome: '$5,200/month'
    },
    { 
      id: 'medical', 
      name: 'Medical', 
      icon: '🏥',
      liveStreams: ['Surgery Stream Live', 'Emergency Room Cam', 'Patient Recovery Monitor'],
      specialists: ['ICU Nurse 30-Year Expert', 'Surgery Outcome Predictor', 'Emergency Response Pro'],
      retiredExperts: 892,
      avgIncome: '$8,100/month'
    },
    { 
      id: 'sports', 
      name: 'Sports', 
      icon: '⚽',
      liveStreams: ['Live NBA Game', 'Soccer World Cup', 'Tennis Championship'],
      specialists: ['Basketball Analytics Pro', 'Soccer Performance Expert', 'Tennis Technique Specialist'],
      retiredExperts: 1234,
      avgIncome: '$6,500/month'
    },
    { 
      id: 'education', 
      name: 'Education', 
      icon: '🎓',
      liveStreams: ['Classroom Live Stream', 'Student Assessment Cam', 'Teaching Methods Live'],
      specialists: ['Classroom Behavior Expert', 'Learning Outcome Predictor', 'Student Engagement Pro'],
      retiredExperts: 678,
      avgIncome: '$4,800/month'
    },
    { 
      id: 'entertainment', 
      name: 'Entertainment', 
      icon: '🎬',
      liveStreams: ['Cooking Competition Live', 'Music Performance Stream', 'Award Show Broadcast'],
      specialists: ['Audience Reaction Expert', 'Performance Quality Pro', 'Entertainment Outcome Predictor'],
      retiredExperts: 543,
      avgIncome: '$5,700/month'
    }
  ];

  const predictionTypes: Record<string, string[]> = {
    construction: [
      'Project completion timing',
      'Equipment failure predictions',
      'Safety incident likelihood',
      'Weather impact assessment',
      'Material delivery accuracy',
      'Worker efficiency patterns'
    ],
    medical: [
      'Surgery duration estimates',
      'Patient response predictions',
      'Equipment needs forecasting',
      'Recovery timeline assessment',
      'Complication likelihood',
      'Treatment effectiveness'
    ],
    sports: [
      'Player performance metrics',
      'Game outcome predictions',
      'Injury risk assessment',
      'Strategy effectiveness',
      'Audience engagement levels',
      'Brand visibility tracking'
    ],
    education: [
      'Student engagement levels',
      'Learning outcome predictions',
      'Behavioral pattern analysis',
      'Technology usage effectiveness',
      'Assessment result forecasting',
      'Classroom dynamics'
    ],
    entertainment: [
      'Audience reaction intensity',
      'Performance quality scores',
      'Technical issue predictions',
      'Social media buzz forecasting',
      'Award outcome predictions',
      'Brand mention frequency'
    ]
  };

  const currentIndustry = industries.find(ind => ind.id === activeIndustry);

  useEffect(() => {
    // Simulate real-time stream analytics
    const interval = setInterval(() => {
      setStreamAnalytics({
        viewerCount: Math.floor(Math.random() * 50000) + 10000,
        activePredictions: Math.floor(Math.random() * 1000) + 500,
        expertParticipation: Math.floor(Math.random() * 100) + 50,
        familyGroups: Math.floor(Math.random() * 200) + 100,
        retiredExperts: Math.floor(Math.random() * 50) + 25
      });
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const handleCreateFamilyGroup = () => {
    setFamilyGroup({
      id: 'family_' + Date.now(),
      members: ['Dad', 'Mom', 'Kid 1', 'Kid 2'],
      sharedSpecialist: selectedSpecialist,
      predictions: [],
      collaborativeScore: 0
    });
  };

  const handleJoinPredictionCluster = (clusterType: string) => {
    const newCluster: PredictionCluster = {
      id: `cluster_${Date.now()}`,
      type: clusterType,
      industry: activeIndustry,
      participants: Math.floor(Math.random() * 500) + 100,
      specialist: selectedSpecialist
    };
    setPredictionClusters([...predictionClusters, newCluster]);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 text-white">
      {/* Header */}
      <div className="bg-black/20 backdrop-blur-sm border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-yellow-400 to-orange-500 bg-clip-text text-transparent">
              Universal Prediction Experience
            </h1>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setRetirementMode(!retirementMode)}
                className={`px-4 py-2 rounded-lg transition-all ${
                  retirementMode 
                    ? 'bg-green-600 text-white' 
                    : 'bg-white/10 hover:bg-white/20'
                }`}
              >
                {retirementMode ? '💰 Retirement Mode ON' : '👤 Switch to Retirement Mode'}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          
          {/* Industry Selection Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10">
              <h2 className="text-xl font-bold mb-4">Select Industry</h2>
              <div className="space-y-3">
                {industries.map(industry => (
                  <button
                    key={industry.id}
                    onClick={() => setActiveIndustry(industry.id)}
                    className={`w-full p-4 rounded-lg transition-all text-left ${
                      activeIndustry === industry.id
                        ? 'bg-gradient-to-r from-purple-600 to-blue-600 transform scale-105'
                        : 'bg-white/10 hover:bg-white/20'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">{industry.icon}</span>
                      <div>
                        <div className="font-bold">{industry.name}</div>
                        <div className="text-sm opacity-70">
                          {industry.retiredExperts} experts • {industry.avgIncome}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {retirementMode && (
                <div className="mt-6 p-4 bg-green-600/20 rounded-lg border border-green-400/30">
                  <h3 className="font-bold text-green-400 mb-2">💰 Retirement Opportunity</h3>
                  <p className="text-sm">
                    As a retired {activeIndustry} professional, you could earn{' '}
                    <span className="font-bold text-yellow-400">
                      {currentIndustry?.avgIncome}
                    </span>{' '}
                    from your expertise!
                  </p>
                  <button className="mt-2 bg-green-600 hover:bg-green-500 px-3 py-1 rounded text-sm">
                    Start Earning Now
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-3">
            
            {/* Live Stream & Analytics */}
            <div className="bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10 mb-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">
                  {currentIndustry?.icon} {currentIndustry?.name} Live Streams
                </h2>
                <div className="flex items-center space-x-4 text-sm">
                  <span className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                    <span>LIVE</span>
                  </span>
                  <span>{streamAnalytics.viewerCount?.toLocaleString()} viewers</span>
                  <span>{streamAnalytics.activePredictions} active predictions</span>
                </div>
              </div>

              {/* Simulated Video Stream */}
              <div className="bg-black rounded-lg aspect-video mb-4 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 to-purple-600/20"></div>
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <div className="text-6xl mb-4">{currentIndustry?.icon}</div>
                    <div className="text-xl font-bold">Live {currentIndustry?.name} Stream</div>
                    <div className="text-sm opacity-70">
                      {currentIndustry?.liveStreams[0]}
                    </div>
                  </div>
                </div>
                
                {/* Real-time prediction overlays */}
                <div className="absolute top-4 left-4 bg-black/70 rounded-lg p-2">
                  <div className="text-xs font-bold text-yellow-400">ACTIVE PREDICTIONS</div>
                  <div className="text-sm">{streamAnalytics.activePredictions} ongoing</div>
                </div>
                
                <div className="absolute top-4 right-4 bg-black/70 rounded-lg p-2">
                  <div className="text-xs font-bold text-green-400">EXPERTS ONLINE</div>
                  <div className="text-sm">{streamAnalytics.retiredExperts} retired pros</div>
                </div>
                
                <div className="absolute bottom-4 left-4 bg-black/70 rounded-lg p-2">
                  <div className="text-xs font-bold text-purple-400">FAMILY GROUPS</div>
                  <div className="text-sm">{streamAnalytics.familyGroups} watching together</div>
                </div>
              </div>

              {/* Stream Selection */}
              <div className="grid grid-cols-3 gap-3">
                {currentIndustry?.liveStreams.map((stream, index) => (
                  <button
                    key={index}
                    className="p-3 bg-white/10 hover:bg-white/20 rounded-lg transition-all text-sm"
                  >
                    <div className="font-bold">{stream}</div>
                    <div className="text-xs opacity-70">
                      {Math.floor(Math.random() * 10000) + 1000} viewers
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Specialist Selection & Social Features */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              
              {/* Specialist Marketplace */}
              <div className="bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10">
                <h3 className="text-xl font-bold mb-4">🎯 Select Your Specialist</h3>
                <div className="space-y-3">
                  {currentIndustry?.specialists.map((specialist, index) => (
                    <button
                      key={index}
                      onClick={() => setSelectedSpecialist(specialist)}
                      className={`w-full p-3 rounded-lg transition-all text-left ${
                        selectedSpecialist === specialist
                          ? 'bg-yellow-600/30 border border-yellow-400'
                          : 'bg-white/10 hover:bg-white/20'
                      }`}
                    >
                      <div className="font-bold">{specialist}</div>
                      <div className="text-sm opacity-70">
                        {Math.floor(Math.random() * 95) + 75}% accuracy • 
                        {Math.floor(Math.random() * 5000) + 1000} followers
                      </div>
                      <div className="text-xs text-green-400">
                        ${Math.floor(Math.random() * 100) + 50}/month subscription
                      </div>
                    </button>
                  ))}
                </div>
                
                {selectedSpecialist && (
                  <div className="mt-4 p-3 bg-yellow-600/20 rounded-lg border border-yellow-400/30">
                    <div className="text-sm font-bold text-yellow-400">Following: {selectedSpecialist}</div>
                    <div className="text-xs">You'll receive their predictions and insights</div>
                  </div>
                )}
              </div>

              {/* Family & Social Features */}
              <div className="bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10">
                <h3 className="text-xl font-bold mb-4">👨‍👩‍👧‍👦 Social Viewing</h3>
                
                {!familyGroup ? (
                  <div>
                    <p className="text-sm opacity-70 mb-4">
                      Watch together with family! Each member can focus on different predictions while following the same specialist.
                    </p>
                    <button
                      onClick={handleCreateFamilyGroup}
                      disabled={!selectedSpecialist}
                      className="w-full bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 rounded-lg transition-all"
                    >
                      Create Family Group
                    </button>
                    {!selectedSpecialist && (
                      <p className="text-xs text-yellow-400 mt-2">Select a specialist first</p>
                    )}
                  </div>
                ) : (
                  <div>
                    <div className="bg-purple-600/20 rounded-lg p-3 mb-3">
                      <div className="font-bold">Family Group Active</div>
                      <div className="text-sm">Following: {familyGroup.sharedSpecialist}</div>
                      <div className="text-xs opacity-70">
                        Members: {familyGroup.members.join(', ')}
                      </div>
                    </div>
                    <div className="text-sm">
                      <div>• Dad: Equipment predictions</div>
                      <div>• Mom: Safety assessments</div>
                      <div>• Kid 1: Timing estimates</div>
                      <div>• Kid 2: Weather impact</div>
                    </div>
                  </div>
                )}

                <div className="mt-4">
                  <h4 className="font-bold mb-2">🎯 Join Prediction Clusters</h4>
                  <div className="space-y-2">
                    {predictionTypes[activeIndustry]?.slice(0, 3).map((type: string, index: number) => (
                      <button
                        key={index}
                        onClick={() => handleJoinPredictionCluster(type)}
                        className="w-full text-left p-2 bg-white/10 hover:bg-white/20 rounded text-sm transition-all"
                      >
                        {type} ({Math.floor(Math.random() * 500) + 100} participants)
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Active Prediction Clusters */}
            {predictionClusters.length > 0 && (
              <div className="bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10 mb-6">
                <h3 className="text-xl font-bold mb-4">🌍 Your Active Prediction Clusters</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {predictionClusters.map((cluster) => (
                    <div key={cluster.id} className="bg-white/10 rounded-lg p-4">
                      <div className="font-bold">{cluster.type}</div>
                      <div className="text-sm opacity-70">
                        {cluster.participants} participants • Following {cluster.specialist}
                      </div>
                      <div className="text-xs text-green-400 mt-1">
                        Active in {cluster.industry} streams
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Prediction Interface */}
            <div className="bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10">
              <h3 className="text-xl font-bold mb-4">🔮 Make Predictions</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {predictionTypes[activeIndustry]?.map((predictionType: string, index: number) => (
                  <div key={index} className="bg-white/10 rounded-lg p-4">
                    <div className="font-bold text-sm mb-2">{predictionType}</div>
                    
                    {selectedSpecialist && (
                      <div className="text-xs text-yellow-400 mb-2">
                        💡 {selectedSpecialist} suggests: {Math.floor(Math.random() * 100)}% likelihood
                      </div>
                    )}
                    
                    <div className="space-y-2">
                      <label htmlFor={`prediction-${index}`} className="sr-only">
                        Prediction likelihood for {predictionType}
                      </label>
                      <input
                        id={`prediction-${index}`}
                        type="range"
                        min="0"
                        max="100"
                        className="w-full"
                        defaultValue={Math.floor(Math.random() * 100)}
                        title={`Adjust likelihood for ${predictionType}`}
                      />
                      <div className="flex justify-between text-xs">
                        <span>Unlikely</span>
                        <span>Very Likely</span>
                      </div>
                    </div>
                    
                    <button className="w-full mt-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 px-3 py-2 rounded text-sm transition-all">
                      Submit Prediction
                    </button>
                  </div>
                ))}
              </div>

              {familyGroup && (
                <div className="mt-6 p-4 bg-purple-600/20 rounded-lg border border-purple-400/30">
                  <h4 className="font-bold text-purple-400 mb-2">👨‍👩‍👧‍👦 Family Collaboration Mode</h4>
                  <p className="text-sm">
                    Your predictions are shared with your family group. Work together using insights from{' '}
                    <span className="font-bold text-yellow-400">{selectedSpecialist}</span>!
                  </p>
                </div>
              )}
            </div>

            {/* Gift Economy & Inheritance Features */}
            <div className="mt-6 bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10">
              <h3 className="text-xl font-bold mb-4">🎁 Gift Economy & Inheritance</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-yellow-600/20 to-orange-600/20 rounded-lg p-4 border border-yellow-400/30">
                  <h4 className="font-bold text-yellow-400 mb-2">💝 Gift Predictions</h4>
                  <p className="text-sm mb-3">
                    Give specialist subscriptions or prediction models as meaningful gifts
                  </p>
                  <button className="w-full bg-yellow-600 hover:bg-yellow-500 px-3 py-2 rounded text-sm">
                    Browse Giftable Assets
                  </button>
                </div>
                
                <div className="bg-gradient-to-br from-green-600/20 to-blue-600/20 rounded-lg p-4 border border-green-400/30">
                  <h4 className="font-bold text-green-400 mb-2">🏛️ Build Inheritance</h4>
                  <p className="text-sm mb-3">
                    Create transferable wealth through watching and expertise building
                  </p>
                  <button className="w-full bg-green-600 hover:bg-green-500 px-3 py-2 rounded text-sm">
                    Start Wealth Building
                  </button>
                </div>
                
                <div className="bg-gradient-to-br from-purple-600/20 to-pink-600/20 rounded-lg p-4 border border-purple-400/30">
                  <h4 className="font-bold text-purple-400 mb-2">🎓 Pass Down Expertise</h4>
                  <p className="text-sm mb-3">
                    Transfer specialist relationships and prediction models to family
                  </p>
                  <button className="w-full bg-purple-600 hover:bg-purple-500 px-3 py-2 rounded text-sm">
                    Manage Inheritance
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 