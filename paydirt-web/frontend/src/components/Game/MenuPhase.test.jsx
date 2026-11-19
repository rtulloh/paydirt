import { useGameStore } from '../../store/gameStore'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import MenuPhase from './MenuPhase'

describe('MenuPhase', () => {
  const mockOnNewGame = vi.fn()
  const mockOnOpenGuide = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders PAYDIRT title', () => {
    render(<MenuPhase onNewGame={mockOnNewGame} onOpenGuide={mockOnOpenGuide} />)
    
    expect(screen.getByText(/PAYDIRT/i)).toBeInTheDocument()
  })

  it('renders new game button', () => {
    render(<MenuPhase onNewGame={mockOnNewGame} onOpenGuide={mockOnOpenGuide} />)
    
    expect(screen.getByRole('button', { name: /NEW GAME/i })).toBeInTheDocument()
  })

  it('calls onNewGame when new game button clicked', () => {
    render(<MenuPhase onNewGame={mockOnNewGame} onOpenGuide={mockOnOpenGuide} />)
    
    fireEvent.click(screen.getByRole('button', { name: /NEW GAME/i }))
    
    expect(mockOnNewGame).toHaveBeenCalled()
  })

  it('renders guide button', () => {
    render(<MenuPhase onNewGame={mockOnNewGame} onOpenGuide={mockOnOpenGuide} />)
    
    expect(screen.getByRole('button', { name: /GUIDE/i })).toBeInTheDocument()
  })

  it('calls onOpenGuide when guide button clicked', () => {
    render(<MenuPhase onNewGame={mockOnNewGame} onOpenGuide={mockOnOpenGuide} />)
    
    fireEvent.click(screen.getByRole('button', { name: /GUIDE/i }))
    
    expect(mockOnOpenGuide).toHaveBeenCalled()
  })
})
it('opens seasons and durable saved games from the menu', () => {
  const onOpenSeasons = vi.fn(), onOpenSaves = vi.fn();
  render(<MenuPhase onOpenSeasons={onOpenSeasons} onOpenSaves={onOpenSaves} />);
  fireEvent.click(screen.getByRole('button', { name: 'SEASONS' }));
  fireEvent.click(screen.getByRole('button', { name: 'SAVED GAMES' }));
  expect(onOpenSeasons).toHaveBeenCalledOnce();
  expect(onOpenSaves).toHaveBeenCalledOnce();
});

it('routes Load Game to durable saves even when old local-storage data exists',()=>{
 const legacy='{"gameId":"obsolete-session","ballPosition":20}';
 localStorage.setItem('paydirt_save',legacy);
 const original=useGameStore.getState().loadGame;
 const oldLoader=vi.fn(()=>true),onOpenSaves=vi.fn();
 useGameStore.setState({gamePhase:'menu',loadGame:oldLoader});
 try {
  render(<MenuPhase onOpenSaves={onOpenSaves}/>);
  fireEvent.click(screen.getByRole('button',{name:'LOAD GAME',exact:true}));
  expect(onOpenSaves).toHaveBeenCalledOnce();
  expect(oldLoader).not.toHaveBeenCalled();
  expect(localStorage.getItem('paydirt_save')).toBe(legacy);
 } finally {localStorage.removeItem('paydirt_save');useGameStore.setState({loadGame:original});}
});
