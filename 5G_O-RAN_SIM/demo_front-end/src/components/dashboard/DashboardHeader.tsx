'use client'

import { useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { 
  Play, 
  Pause, 
  Square, 
  Settings, 
  Activity, 
  Shield, 
  Zap,
  Server,
  Radio,
  Clock,
  Network
} from 'lucide-react'

interface DashboardHeaderProps {
  simulationStatus: 'stopped' | 'running' | 'paused'
  onSimulationToggle: (status: 'stopped' | 'running' | 'paused') => void
  onStartDemo: () => void
  activeView: 'dashboard' | 'analysis' | 'config' | 'oran'
  onViewChange: (view: 'dashboard' | 'analysis' | 'config' | 'oran') => void
  networkStats: {
    onlineNfs: number
    activeSessions: number
    avgLatency: number
  }
}

export function DashboardHeader({
  simulationStatus,
  onSimulationToggle,
  onStartDemo,
  activeView,
  onViewChange,
  networkStats,
}: DashboardHeaderProps) {
  const statusLabel = useMemo(
    () => simulationStatus.charAt(0).toUpperCase() + simulationStatus.slice(1),
    [simulationStatus]
  )

  const handleSimulationControl = (action: 'start' | 'pause' | 'stop') => {
    switch (action) {
      case 'start':
        onViewChange('analysis')
        onStartDemo()
        break
      case 'pause':
        onSimulationToggle('paused')
        break
      case 'stop':
        onSimulationToggle('stopped')
        break
    }
  }

  return (
    <div className="border-b bg-card">
      <div className="flex items-center justify-between p-4">
        
        {/* Logo and Title */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Shield className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-2xl font-bold">5G Mission Control</h1>
              <p className="text-sm text-muted-foreground">BlueField-3 DPU Network Simulator</p>
            </div>
          </div>
          
          <Badge variant={
            simulationStatus === 'running' ? 'default' : 
            simulationStatus === 'paused' ? 'secondary' : 
            'outline'
          }>
            {simulationStatus === 'running' && <Activity className="w-3 h-3 mr-1" />}
            {simulationStatus === 'paused' && <Pause className="w-3 h-3 mr-1" />}
            {simulationStatus === 'stopped' && <Square className="w-3 h-3 mr-1" />}
            {statusLabel}
          </Badge>
        </div>

        {/* View Switcher */}
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1 p-1 bg-muted rounded-lg">
            <Button
              variant={activeView === 'dashboard' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => onViewChange('dashboard')}
              className="flex items-center space-x-1"
            >
              <Server className="w-4 h-4" />
              <span>Live Dashboard</span>
            </Button>
            <Button
              variant={activeView === 'analysis' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => onViewChange('analysis')}
              className="flex items-center space-x-1"
            >
              <Activity className="w-4 h-4" />
              <span>Procedure Analysis</span>
            </Button>
            <Button
              variant={activeView === 'config' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => onViewChange('config')}
              className="flex items-center space-x-1"
            >
              <Settings className="w-4 h-4" />
              <span>Configuration</span>
            </Button>
            <Button
              variant={activeView === 'oran' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => onViewChange('oran')}
              className="flex items-center space-x-1"
            >
              <Network className="w-4 h-4" />
              <span>O-RAN</span>
            </Button>
          </div>
        </div>

        {/* Global Simulation Controls */}
        <div className="flex items-center space-x-2">
          <Card className="px-3 py-2">
            <div className="flex items-center space-x-2">
              <Button
                variant={simulationStatus === 'running' ? 'secondary' : 'default'}
                size="sm"
                onClick={() => handleSimulationControl('start')}
              >
                <Play className="w-4 h-4 mr-1" />
                Start
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleSimulationControl('pause')}
                disabled={simulationStatus === 'stopped'}
              >
                <Pause className="w-4 h-4 mr-1" />
                Pause
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => handleSimulationControl('stop')}
                disabled={simulationStatus === 'stopped'}
              >
                <Square className="w-4 h-4 mr-1" />
                Stop
              </Button>
            </div>
          </Card>

          {/* Quick Stats */}
          <Card className="px-3 py-2">
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center space-x-1">
                <Radio className="w-4 h-4 text-green-500" />
                <span>{networkStats.onlineNfs} NFs Online</span>
              </div>
              <div className="flex items-center space-x-1">
                <Zap className="w-4 h-4 text-blue-500" />
                <span>{networkStats.activeSessions} Active Sessions</span>
              </div>
              <div className="flex items-center space-x-1">
                <Clock className="w-4 h-4 text-orange-500" />
                <span>{networkStats.avgLatency}ms Avg Latency</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
