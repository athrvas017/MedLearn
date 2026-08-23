import React, { useState, useRef } from 'react';

interface InputBarProps {
  onSend: (query: string, imageFile?: File | null, generateQuiz?: boolean) => void;
  isLoading: boolean;
}

export const InputBar: React.FC<InputBarProps> = ({ onSend, isLoading }) => {
  const [query, setQuery] = useState('');
  const [generateQuiz, setGenerateQuiz] = useState(false);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const samplePrompts = [
    'Explain action potentials in myocardial cells with phases & ion channels.',
    'What are the four chambers of the heart and valves that separate them?',
    'Explain the countercurrent multiplier mechanism in the nephron loop.',
    'Describe the histology and layers of the pericardium.',
  ];

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onload = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const removeImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() && !selectedImage) return;
    if (isLoading) return;

    onSend(query.trim() || 'Explain this medical diagram', selectedImage, generateQuiz);
    setQuery('');
    removeImage();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full flex flex-col gap-2">
      {/* Sample Prompt Chips (when input is empty) */}
      {!query && !selectedImage && (
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
          {samplePrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => setQuery(p)}
              className="px-3 py-1.5 rounded-full bg-surface-variant/10 hover:bg-primary/20 text-outline-variant hover:text-primary-fixed border border-outline-variant/20 hover:border-primary/40 text-xs font-sans whitespace-nowrap transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[13px]">lightbulb</span>
              <span className="truncate max-w-xs">{p}</span>
            </button>
          ))}
        </div>
      )}

      {/* Main Glassmorphic Input Box */}
      <form
        onSubmit={handleSubmit}
        className="glass rounded-2xl p-2.5 md:p-3 border border-outline/30 focus-within:border-primary/60 focus-within:ring-2 focus-within:ring-primary/20 transition-all shadow-xl flex flex-col gap-2 relative bg-inverse-surface/90"
      >
        {/* Attached Image Preview */}
        {imagePreview && (
          <div className="flex items-center gap-2.5 p-2 rounded-xl bg-surface-variant/20 border border-outline-variant/30 w-fit">
            <img
              src={imagePreview}
              alt="Preview"
              className="w-12 h-12 object-cover rounded-lg border border-outline-variant/40"
            />
            <div className="flex flex-col">
              <span className="text-xs font-mono text-primary-fixed font-semibold truncate max-w-xs">
                {selectedImage?.name}
              </span>
              <span className="text-[10px] text-outline-variant font-mono">
                Multimodal Image Attachment
              </span>
            </div>
            <button
              type="button"
              onClick={removeImage}
              className="p-1 rounded-full hover:bg-surface-variant/40 text-outline-variant hover:text-danger-crimson ml-1 transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>
        )}

        {/* Text Input Area */}
        <div className="flex items-end gap-2">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Ask a medical question, explain a diagram, or test anatomy concepts..."
            className="w-full bg-transparent text-surface-subtle placeholder-outline-variant/60 text-[15px] resize-none outline-none py-1.5 px-2 font-sans min-h-[44px] max-h-32"
          />

          {/* Hidden File Input */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleImageChange}
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
          />

          {/* Action Buttons */}
          <div className="flex items-center gap-1.5">
            {/* Image Upload Trigger */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className={`p-2.5 rounded-xl transition-all cursor-pointer ${
                selectedImage
                  ? 'bg-primary/30 text-primary-fixed border border-primary/50'
                  : 'hover:bg-surface-variant/20 text-outline-variant hover:text-primary-fixed border border-transparent'
              }`}
              title="Upload anatomical diagram or histological slide (PNG/JPG)"
            >
              <span className="material-symbols-outlined text-[22px]">image</span>
            </button>

            {/* Quiz Toggle Button */}
            <button
              type="button"
              onClick={() => setGenerateQuiz(!generateQuiz)}
              className={`px-3 py-2 rounded-xl text-xs font-medium transition-all flex items-center gap-1.5 border cursor-pointer ${
                generateQuiz
                  ? 'bg-secondary-container/20 text-secondary-container border-secondary-container/50 shadow-sm'
                  : 'hover:bg-surface-variant/20 text-outline-variant border-transparent'
              }`}
              title="Toggle automatic practice quiz generation"
            >
              <span
                className="material-symbols-outlined text-[18px]"
                style={generateQuiz ? { fontVariationSettings: "'FILL' 1" } : {}}
              >
                quiz
              </span>
              <span className="hidden sm:inline">Quiz</span>
            </button>

            {/* Send Button */}
            <button
              type="submit"
              disabled={isLoading || (!query.trim() && !selectedImage)}
              className={`p-2.5 rounded-xl transition-all flex items-center justify-center cursor-pointer ${
                isLoading || (!query.trim() && !selectedImage)
                  ? 'bg-surface-variant/20 text-outline-variant/40 cursor-not-allowed'
                  : 'bg-primary hover:bg-primary-container text-on-primary glow-teal active:scale-95'
              }`}
            >
              {isLoading ? (
                <span className="material-symbols-outlined text-[22px] animate-spin">
                  autorenew
                </span>
              ) : (
                <span className="material-symbols-outlined text-[22px]">send</span>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};
