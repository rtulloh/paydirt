import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import MenuPhase from './MenuPhase';

vi.mock('../../runtime/gameFetch', () => ({ browserMode: true }));

it('offers public seasons and explains browser save ownership', () => {
  render(<MenuPhase />);
  expect(screen.getByText(/public seasons/i)).toHaveTextContent(/1977.*1983.*2024.*2026/);
  expect(screen.getByText(/same browser profile/i)).toBeVisible();
  expect(screen.getByRole('button', { name: 'NEW GAME' })).toBeEnabled();
});
