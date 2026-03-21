import { useCallback } from 'react';
import { useGameStore } from '../store/gameStore';
import { API_BASE } from '../../config';

interface PenaltyData {
  description?: string;
  yards?: number;
  turnover?: boolean;
  touchdown?: boolean;
  pending_penalty_decision?: boolean;
  penalty_choice?: {
    penalty_options?: Array<{
      penalty_type?: string;
      raw_result?: string;
      yards?: number;
      description?: string;
      auto_first_down?: boolean;
      is_pass_interference?: boolean;
    }>;
    offended_team?: string;
    offsetting?: boolean;
    is_pass_interference?: boolean;
    reroll_log?: string[];
  } | null;
}

interface UsePenaltyHandlingReturn {
  handlePenaltyDecision: (acceptPenalty: boolean, penaltyIndex: number) => Promise<void>;
  isProcessing: boolean;
}

export function usePenaltyHandling(): UsePenaltyHandlingReturn {
  const store = useGameStore();
  const { gameId, updateGameState } = store;

  const handlePenaltyDecision = useCallback(async (
    acceptPenalty: boolean, 
    penaltyIndex: number = 0
  ) => {
    if (!gameId) {
      console.error('No game ID for penalty decision');
      return;
    }
    
    try {
      const body = {
        game_id: gameId,
        penalty_index: Number(penaltyIndex) || 0,
        accept_penalty: Boolean(acceptPenalty),
      };
      
      const res = await fetch(`${API_BASE}/api/game/penalty-decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      
      if (res.ok) {
        const data = await res.json();
        updateGameState(data.game_state);
      } else {
        const error = await res.text();
        console.error('Penalty decision failed:', res.status, error);
      }
    } catch (err) {
      console.error('Failed to handle penalty decision:', err);
    }
  }, [gameId, updateGameState]);

  return {
    handlePenaltyDecision,
    isProcessing: false,
  };
}

export function extractPenaltyInfo(penaltyData: PenaltyData | null): {
  isOffsetting: boolean;
  offendedTeam: string | null;
  options: Array<{
    description: string;
    yards: number;
    autoFirstDown: boolean;
  }>;
  playResultYards: number;
  hasTurnover: boolean;
  hasTouchdown: boolean;
} | null {
  if (!penaltyData?.penalty_choice) {
    return null;
  }

  const penalty_choice = penaltyData.penalty_choice;
  
  return {
    isOffsetting: penalty_choice.offsetting || false,
    offendedTeam: penalty_choice.offended_team || null,
    options: (penalty_choice.penalty_options || []).map(opt => ({
      description: opt.description || '',
      yards: opt.yards || 0,
      autoFirstDown: opt.auto_first_down || false,
    })),
    playResultYards: penaltyData.yards || 0,
    hasTurnover: penaltyData.turnover || false,
    hasTouchdown: penaltyData.touchdown || false,
  };
}
