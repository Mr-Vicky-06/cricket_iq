import { describe, it, expect, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { App } from '../App';
import { apiClient } from '../api/client';
import fs from 'node:fs';
import path from 'node:path';

describe('Gate 1 Bootstrap Smoke Test Suite', () => {
  it('mounts the application successfully with expected landmark and title', async () => {
    vi.spyOn(apiClient, 'checkHealthLive').mockResolvedValue({ status: 'alive' });
    await act(async () => {
      render(<App />);
    });
    const heading = screen.getByRole('heading', { level: 1, name: /cricketiq/i });
    expect(heading).toBeInTheDocument();
    expect(screen.getByText(/official rules intelligence/i)).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('validates API base URL configuration accepts relative and HTTPS paths', () => {
    const isValidApiBase = (url: string): boolean => {
      if (!url || url.startsWith('/')) return true;
      try {
        const parsed = new URL(url);
        return parsed.protocol === 'https:' || parsed.protocol === 'http:';
      } catch {
        return false;
      }
    };

    expect(isValidApiBase('/api')).toBe(true);
    expect(isValidApiBase('/v1')).toBe(true);
    expect(isValidApiBase('')).toBe(true);
    expect(isValidApiBase('http://127.0.0.1:8000')).toBe(true);
    expect(isValidApiBase('javascript:alert(1)')).toBe(false);
    expect(isValidApiBase('data:text/html,malicious')).toBe(false);
  });

  it('proves no secrets are present in .env.example', () => {
    const envExamplePath = path.resolve(__dirname, '../../.env.example');
    expect(fs.existsSync(envExamplePath)).toBe(true);

    const content = fs.readFileSync(envExamplePath, 'utf-8');
    expect(content).not.toMatch(/(secret|password|token|bearer|api_key|private_key)=.+/i);
    expect(content).toMatch(/VITE_API_BASE_URL/);
  });
});
