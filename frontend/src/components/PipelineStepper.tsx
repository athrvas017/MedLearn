import React from 'react';
import { PipelineStep } from '../types';

interface PipelineStepperProps {
  steps: PipelineStep[];
}

export const PipelineStepper: React.FC<PipelineStepperProps> = ({ steps }) => {
  return (
    <div className="glass rounded-xl p-4 flex items-center justify-between relative overflow-hidden mb-4 border border-outline/20">
      <div className="absolute inset-0 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent pointer-events-none" />

      {steps.map((step, idx) => {
        const isRunning = step.status === 'running';
        const isDone = step.status === 'done';
        const isIdle = step.status === 'idle';
        const isError = step.status === 'error';

        return (
          <React.Fragment key={step.id}>
            {/* Step Node */}
            <div
              className={`flex flex-col items-center z-10 transition-all duration-300 ${
                isIdle ? 'opacity-40' : 'opacity-100'
              }`}
            >
              <div className="relative">
                {isRunning && (
                  <div className="absolute -inset-1 rounded-full border-2 border-primary-fixed animate-pulse-ring" />
                )}
                <div
                  className={`w-9 h-9 rounded-full flex items-center justify-center mb-1 text-sm font-semibold transition-all duration-300 ${
                    isRunning
                      ? 'bg-primary text-on-primary glow-teal scale-105'
                      : isDone
                      ? 'bg-primary/20 text-primary-fixed border border-primary/40'
                      : isError
                      ? 'bg-danger-crimson/20 text-danger-crimson border border-danger-crimson/40'
                      : 'bg-surface-variant/20 text-outline-variant border border-outline-variant/30'
                  }`}
                >
                  <span className="material-symbols-outlined text-[17px]">
                    {isDone ? 'check' : step.icon}
                  </span>
                </div>
              </div>
              <span
                className={`text-[11px] font-sans font-medium whitespace-nowrap ${
                  isRunning
                    ? 'text-primary-fixed font-semibold'
                    : isDone
                    ? 'text-surface-subtle'
                    : 'text-outline-variant'
                }`}
              >
                {step.label}
              </span>
            </div>

            {/* Connector Bar */}
            {idx < steps.length - 1 && (
              <div
                className={`flex-1 h-[1.5px] mx-2 transition-colors duration-300 ${
                  isDone
                    ? 'bg-primary/50'
                    : isRunning
                    ? 'bg-gradient-to-r from-primary/60 to-outline-variant/30 animate-pulse'
                    : 'bg-outline-variant/20'
                }`}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
