import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QuestionInput } from './QuestionInput';

describe('QuestionInput Component', () => {
  it('renders input with placeholder and character count', () => {
    render(
      <QuestionInput
        query="What is a free hit?"
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        isLoading={false}
      />
    );

    const textarea = screen.getByRole('textbox');
    expect(textarea).toBeInTheDocument();
    expect(textarea).toHaveValue('What is a free hit?');
    expect(screen.getByText('19/1000 characters')).toBeInTheDocument();
  });

  it('disables submit button when query is under 3 characters', () => {
    render(
      <QuestionInput
        query="hi"
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        isLoading={false}
      />
    );

    const btn = screen.getByRole('button', { name: /ask cricketiq/i });
    expect(btn).toBeDisabled();
  });

  it('calls onSubmit when valid query is submitted via button click', () => {
    const handleSubmit = vi.fn();
    render(
      <QuestionInput
        query="Can a batter be run out?"
        onChange={vi.fn()}
        onSubmit={handleSubmit}
        isLoading={false}
      />
    );

    const btn = screen.getByRole('button', { name: /ask cricketiq/i });
    expect(btn).not.toBeDisabled();
    fireEvent.click(btn);
    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });

  it('calls onSubmit on Enter keydown without shiftKey', () => {
    const handleSubmit = vi.fn();
    render(
      <QuestionInput
        query="Can a batter be run out?"
        onChange={vi.fn()}
        onSubmit={handleSubmit}
        isLoading={false}
      />
    );

    const textarea = screen.getByRole('textbox');
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });
    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });
});
