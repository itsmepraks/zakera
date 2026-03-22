/**
 * Storybook stories for the ModelSelector component.
 *
 * Run with: npx storybook dev -p 6006
 */

import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import ModelSelector, { ModelSelection } from './ModelSelector';

const meta: Meta<typeof ModelSelector> = {
  title: 'Chat/ModelSelector',
  component: ModelSelector,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component:
          'Two-level dropdown for choosing a provider and model. ' +
          'Shows capability badges (streaming, vision, tool calling, code) ' +
          'and context-length / cost-tier metadata for each model.',
      },
    },
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof ModelSelector>;

// Controlled wrapper so Storybook can show interactive state changes
function ControlledModelSelector(props: Partial<React.ComponentProps<typeof ModelSelector>>) {
  const [value, setValue] = useState<ModelSelection>(
    props.value ?? { provider: 'openai', model: 'gpt-4o' }
  );
  return (
    <div className="p-8">
      <ModelSelector
        {...props}
        value={value}
        onChange={(sel) => {
          setValue(sel);
          console.log('Selected:', sel);
        }}
      />
      <p className="mt-4 text-sm text-gray-500">
        Selected: <code>{JSON.stringify(value)}</code>
      </p>
    </div>
  );
}

export const Default: Story = {
  render: () => <ControlledModelSelector />,
};

export const DefaultOpenAI: Story = {
  render: () => (
    <ControlledModelSelector value={{ provider: 'openai', model: 'gpt-4o' }} />
  ),
  name: 'OpenAI — GPT-4o',
};

export const AnthropicClaude: Story = {
  render: () => (
    <ControlledModelSelector
      value={{ provider: 'anthropic', model: 'claude-3-5-sonnet-20241022' }}
    />
  ),
  name: 'Anthropic — Claude 3.5 Sonnet',
};

export const LocalOllama: Story = {
  render: () => (
    <ControlledModelSelector value={{ provider: 'ollama', model: 'llama3.2' }} />
  ),
  name: 'Ollama — Local (no API key)',
};

export const WithoutCapabilityBadges: Story = {
  render: () => (
    <ControlledModelSelector
      value={{ provider: 'groq', model: 'llama-3.3-70b-versatile' }}
      showCapabilityBadges={false}
      showCostTier={false}
    />
  ),
  name: 'Minimal (no badges)',
};

export const Disabled: Story = {
  render: () => (
    <ControlledModelSelector
      value={{ provider: 'openai', model: 'gpt-4o-mini' }}
      disabled
    />
  ),
};
