'use client';

import React from 'react';
import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 text-white">
      {/* Revolutionary Header */}
      <header className="bg-black/20 backdrop-blur-sm border-b border-white/10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-yellow-400 via-red-500 to-pink-500 bg-clip-text text-transparent">
              Morphine
            </h1>
            <div className="text-sm text-gray-300">
              Universal Human Knowledge Sharing Economy
            </div>
          </div>
          
          <div className="flex items-center space-x-6">
            <div className="text-sm text-green-400 flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span>Revolutionary Platform ACTIVE</span>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div className="mb-8">
            <h1 className="text-6xl md:text-8xl font-bold mb-6 bg-gradient-to-r from-yellow-400 via-red-500 to-pink-500 bg-clip-text text-transparent">
              Revolutionary
            </h1>
            <h2 className="text-4xl md:text-6xl font-bold mb-6">
              Universal Prediction & Expertise Economy
            </h2>
            <p className="text-xl md:text-2xl text-gray-300 max-w-4xl mx-auto mb-8">
              The world's first platform where <span className="text-yellow-400">entertainment creates wealth</span>, 
              <span className="text-green-400"> expertise becomes inheritance</span>, and 
              <span className="text-blue-400"> knowledge becomes universally accessible</span>
            </p>
          </div>

          {/* Revolutionary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12">
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6">
              <div className="text-3xl font-bold text-yellow-400">2,847</div>
              <div className="text-sm text-gray-300">Universal Annotation Models</div>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6">
              <div className="text-3xl font-bold text-green-400">45M</div>
              <div className="text-sm text-gray-300">Videos Enhanced</div>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6">
              <div className="text-3xl font-bold text-blue-400">$2.8M</div>
              <div className="text-sm text-gray-300">Expert Earnings</div>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6">
              <div className="text-3xl font-bold text-purple-400">∞</div>
              <div className="text-sm text-gray-300">Infinite Scalability</div>
            </div>
          </div>

          {/* Revolutionary Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
            <Link href="/universal-prediction" className="group bg-white/10 backdrop-blur-sm rounded-xl p-8 hover:bg-white/20 transition-all duration-300 transform hover:scale-105">
              <div className="text-4xl mb-4">🎯</div>
              <h3 className="text-2xl font-bold mb-4 text-yellow-400">Universal Predictions</h3>
              <p className="text-gray-300 mb-4">
                Transform ANY live content into engaging multi-dimensional prediction experiences across all industries
              </p>
              <div className="text-sm text-green-400">Construction • Medical • Sports • Education • Finance</div>
            </Link>

            <Link href="/annotation-models" className="group bg-white/10 backdrop-blur-sm rounded-xl p-8 hover:bg-white/20 transition-all duration-300 transform hover:scale-105">
              <div className="text-4xl mb-4">🧠</div>
              <h3 className="text-2xl font-bold mb-4 text-blue-400">Knowledge Overlay System</h3>
              <p className="text-gray-300 mb-4">
                Any expert can create annotation models that enhance unlimited videos globally
              </p>
              <div className="text-sm text-green-400">Create Once • Earn Forever • Infinite Scalability</div>
            </Link>

            <div className="group bg-white/10 backdrop-blur-sm rounded-xl p-8 hover:bg-white/20 transition-all duration-300 transform hover:scale-105">
              <div className="text-4xl mb-4">💰</div>
              <h3 className="text-2xl font-bold mb-4 text-green-400">Expert Retirement Revolution</h3>
              <p className="text-gray-300 mb-4">
                Every retired professional becomes income-generating consultant with 10+ revenue streams
              </p>
              <div className="text-sm text-green-400">$15,000-$50,000+/month passive income potential</div>
            </div>

            <div className="group bg-white/10 backdrop-blur-sm rounded-xl p-8 hover:bg-white/20 transition-all duration-300 transform hover:scale-105">
              <div className="text-4xl mb-4">🎨</div>
              <h3 className="text-2xl font-bold mb-4 text-red-400">Advertising Revolution</h3>
              <p className="text-gray-300 mb-4">
                No more ad breaks! Companies create engaging prediction opportunities with massive prize pools
              </p>
              <div className="text-sm text-green-400">100x more effective • 3 hours vs 30 seconds engagement</div>
            </div>

            <div className="group bg-white/10 backdrop-blur-sm rounded-xl p-8 hover:bg-white/20 transition-all duration-300 transform hover:scale-105">
              <div className="text-4xl mb-4">👥</div>
              <h3 className="text-2xl font-bold mb-4 text-purple-400">Social Transformation</h3>
              <p className="text-gray-300 mb-4">
                Families bond through collaborative specialist teamwork and multi-dimensional viewing experiences
              </p>
              <div className="text-sm text-green-400">Collaborative Intelligence • Knowledge Inheritance</div>
            </div>

            <div className="group bg-white/10 backdrop-blur-sm rounded-xl p-8 hover:bg-white/20 transition-all duration-300 transform hover:scale-105">
              <div className="text-4xl mb-4">🌍</div>
              <h3 className="text-2xl font-bold mb-4 text-pink-400">Universal Education</h3>
              <p className="text-gray-300 mb-4">
                Every video becomes a potential masterclass with world-class expert overlays
              </p>
              <div className="text-sm text-green-400">Knowledge Democratization • Breaking Down Barriers</div>
            </div>
          </div>

          {/* Revolutionary Call to Action */}
          <div className="text-center">
            <h3 className="text-3xl font-bold mb-6">Join the Revolution</h3>
            <p className="text-xl text-gray-300 mb-8">
              The most ambitious platform ever conceived - transforming entertainment, advertising, expertise, social interaction, and global education simultaneously.
            </p>
            
            <div className="flex flex-col md:flex-row justify-center items-center space-y-4 md:space-y-0 md:space-x-6">
              <Link 
                href="/universal-prediction"
                className="bg-gradient-to-r from-yellow-400 to-red-500 text-black font-bold py-4 px-8 rounded-lg text-lg hover:from-yellow-300 hover:to-red-400 transition-all duration-300 transform hover:scale-105"
              >
                🎯 Start Predicting
              </Link>
              
              <Link 
                href="/annotation-models"
                className="bg-gradient-to-r from-blue-400 to-purple-500 text-white font-bold py-4 px-8 rounded-lg text-lg hover:from-blue-300 hover:to-purple-400 transition-all duration-300 transform hover:scale-105"
              >
                🧠 Create Knowledge Models
              </Link>
            </div>

            <div className="mt-8 text-sm text-gray-400">
              <div className="mb-2">Revolutionary Platform Features Now Available:</div>
              <div className="flex flex-wrap justify-center gap-2">
                <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full">✅ Universal Prediction Economy</span>
                <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full">✅ Expert Retirement Income</span>
                <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full">✅ Brand Engagement Revolution</span>
                <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full">✅ Universal Annotation Models</span>
                <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full">✅ Infinite Knowledge Scalability</span>
                <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full">✅ Global Expert Marketplace</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Revolutionary Footer */}
      <footer className="bg-black/30 backdrop-blur-sm border-t border-white/10 py-8 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div className="text-2xl font-bold mb-4 bg-gradient-to-r from-yellow-400 via-red-500 to-pink-500 bg-clip-text text-transparent">
            We have just created the infrastructure for the first Universal Human Knowledge Sharing Economy in history.
          </div>
          <div className="text-gray-400">
            🚀🌟💫 The revolution starts now. 💫🌟🚀
          </div>
        </div>
      </footer>
    </div>
  );
} 