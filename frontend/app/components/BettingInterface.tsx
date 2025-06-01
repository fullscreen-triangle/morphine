'use client';

import React, { useState, useEffect } from 'react';

interface BettingInterfaceProps {
  streamId: string;
  analytics: any;
}

export const BettingInterface: React.FC<BettingInterfaceProps> = ({ streamId, analytics }) => {
  const [activeBets, setActiveBets] = useState<any[]>([]);
  const [betTypes, setBetTypes] = useState<any[]>([]);
  const [selectedBetType, setSelectedBetType] = useState('');
  const [betAmount, setBetAmount] = useState(10);
  const [prediction, setPrediction] = useState<any>({});
  const [balance, setBalance] = useState(100);

  useEffect(() => {
    fetchBetTypes();
    fetchBalance();
    fetchActiveBets();
  }, [streamId]);

  const fetchBetTypes = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/betting/types`);
      const data = await response.json();
      if (data.success) {
        setBetTypes(data.data);
      }
    } catch (error) {
      console.error('Failed to fetch bet types:', error);
    }
  };

  const fetchBalance = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/betting/balance/${streamId}`, {
        headers: { 'Authorization': 'Bearer demo-token' }
      });
      const data = await response.json();
      if (data.success) {
        setBalance(data.data.available);
      }
    } catch (error) {
      console.error('Failed to fetch balance:', error);
    }
  };

  const fetchActiveBets = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/betting/stream/${streamId}/activity`);
      const data = await response.json();
      if (data.success) {
        setActiveBets(data.data.recentBets.slice(0, 5));
      }
    } catch (error) {
      console.error('Failed to fetch active bets:', error);
    }
  };

  const placeBet = async () => {
    if (!selectedBetType || betAmount <= 0 || betAmount > balance) {
      alert('Invalid bet parameters');
      return;
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/betting/place`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer demo-token'
        },
        body: JSON.stringify({
          streamId,
          betType: selectedBetType,
          amount: betAmount,
          prediction: prediction,
          duration: 60000 // 1 minute
        })
      });

      const data = await response.json();
      if (data.success) {
        alert('Bet placed successfully!');
        fetchBalance();
        fetchActiveBets();
        // Reset form
        setSelectedBetType('');
        setPrediction({});
        setBetAmount(10);
      } else {
        alert(`Failed to place bet: ${data.error}`);
      }
    } catch (error) {
      console.error('Failed to place bet:', error);
      alert('Failed to place bet');
    }
  };

  const renderPredictionForm = () => {
    switch (selectedBetType) {
      case 'speed_milestone':
        return (
          <div className="space-y-2">
            <div>
              <label className="block text-sm">Target Speed (km/h):</label>
              <input
                type="number"
                className="input-field w-full"
                value={prediction.targetSpeed || ''}
                onChange={(e) => setPrediction({...prediction, targetSpeed: parseFloat(e.target.value)})}
                placeholder="e.g., 15"
              />
            </div>
            <div>
              <label className="block text-sm">Direction:</label>
              <select
                className="input-field w-full"
                value={prediction.direction || ''}
                onChange={(e) => setPrediction({...prediction, direction: e.target.value})}
              >
                <option value="">Select...</option>
                <option value="over">Over target speed</option>
                <option value="under">Under target speed</option>
              </select>
            </div>
          </div>
        );
      
      case 'pose_event':
        return (
          <div className="space-y-2">
            <div>
              <label className="block text-sm">Joint:</label>
              <select
                className="input-field w-full"
                value={prediction.joint || ''}
                onChange={(e) => setPrediction({...prediction, joint: e.target.value})}
              >
                <option value="">Select joint...</option>
                <option value="left_knee">Left Knee</option>
                <option value="right_knee">Right Knee</option>
                <option value="left_shoulder">Left Shoulder</option>
                <option value="right_shoulder">Right Shoulder</option>
              </select>
            </div>
            <div>
              <label className="block text-sm">Target Angle (degrees):</label>
              <input
                type="number"
                className="input-field w-full"
                value={prediction.targetAngle || ''}
                onChange={(e) => setPrediction({...prediction, targetAngle: parseFloat(e.target.value)})}
                placeholder="e.g., 90"
              />
            </div>
          </div>
        );
      
      case 'detection_count':
        return (
          <div className="space-y-2">
            <div>
              <label className="block text-sm">Predicted Count:</label>
              <input
                type="number"
                className="input-field w-full"
                value={prediction.count || ''}
                onChange={(e) => setPrediction({...prediction, count: parseInt(e.target.value)})}
                placeholder="e.g., 3"
              />
            </div>
          </div>
        );
      
      default:
        return <div className="text-gray-400">Select a bet type to configure prediction</div>;
    }
  };

  const getBetStatusColor = (status: string) => {
    switch (status) {
      case 'won': return 'text-green-400';
      case 'lost': return 'text-red-400';
      case 'active': return 'text-yellow-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="h-full flex">
      {/* Betting Form */}
      <div className="flex-1 p-4 border-r border-gray-700">
        <h3 className="text-lg font-bold mb-4">💰 Place Bet</h3>
        
        <div className="mb-4">
          <div className="text-sm text-gray-300 mb-2">
            Balance: <span className="text-green-400 font-semibold">${balance.toFixed(2)}</span>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label">Bet Type:</label>
            <select
              className="input-field"
              value={selectedBetType}
              onChange={(e) => {
                setSelectedBetType(e.target.value);
                setPrediction({});
              }}
            >
              <option value="">Select bet type...</option>
              {betTypes.map((type) => (
                <option key={type.name} value={type.name}>
                  {type.description}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Amount ($):</label>
            <input
              type="number"
              className="input-field"
              value={betAmount}
              onChange={(e) => setBetAmount(parseFloat(e.target.value))}
              min="1"
              max={balance}
            />
          </div>

          <div>
            <label className="label">Prediction:</label>
            <div className="bg-gray-700 p-3 rounded">
              {renderPredictionForm()}
            </div>
          </div>

          <button
            className="btn-primary w-full"
            onClick={placeBet}
            disabled={!selectedBetType || betAmount <= 0 || betAmount > balance}
          >
            Place Bet ${betAmount}
          </button>
        </div>

        {/* Current Analytics Context */}
        {analytics && (
          <div className="mt-4 p-3 bg-gray-700 rounded">
            <div className="text-sm font-semibold mb-2">Current Context:</div>
            <div className="text-xs space-y-1">
              {analytics.vibrio && (
                <>
                  <div>Detections: {analytics.vibrio.detections?.length || 0}</div>
                  <div>Max Speed: {Math.max(...(analytics.vibrio.tracks?.map((t: any) => t.speed) || [0])).toFixed(1)} km/h</div>
                </>
              )}
              {analytics.moriarty && analytics.moriarty.pose_detected && (
                <div>Pose Quality: {(analytics.moriarty.pose_quality_score * 100).toFixed(1)}%</div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Recent Bets */}
      <div className="w-80 p-4">
        <h3 className="text-lg font-bold mb-4">🎯 Recent Bets</h3>
        
        <div className="space-y-2">
          {activeBets.length > 0 ? (
            activeBets.map((bet, index) => (
              <div key={index} className="bg-gray-700 p-3 rounded text-sm">
                <div className="flex justify-between items-start mb-1">
                  <div className="font-medium">{bet.betType.replace('_', ' ')}</div>
                  <div className={`font-semibold ${getBetStatusColor(bet.status)}`}>
                    {bet.status.toUpperCase()}
                  </div>
                </div>
                <div className="text-gray-300">
                  Amount: ${bet.amount} | Odds: {bet.odds}x
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {new Date(bet.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))
          ) : (
            <div className="text-gray-400 text-center py-8">
              No recent bets
            </div>
          )}
        </div>

        {/* Betting Statistics */}
        <div className="mt-6 p-3 bg-gray-700 rounded">
          <div className="text-sm font-semibold mb-2">Stream Stats</div>
          <div className="text-xs space-y-1">
            <div>Active Bets: {activeBets.filter(b => b.status === 'active').length}</div>
            <div>Total Volume: ${activeBets.reduce((sum, b) => sum + b.amount, 0).toFixed(2)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}; 