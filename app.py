import React, { useState, useEffect } from 'react';
import { Loader2, Send, Check, X, Sparkles, MessageSquare, AlertTriangle } from 'lucide-react';
import { storageService } from '../services/storageService';
import { geminiService } from '../services/geminiService';
import { Word, PracticeSession } from '../types';

interface PracticeProps {
  apiKey: string;
}

const Practice: React.FC<PracticeProps> = ({ apiKey }) => {
  const [words, setWords] = useState<Word[]>([]);
  const [targetWordInput, setTargetWordInput] = useState('');
  const [sentence, setSentence] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<PracticeSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  useEffect(() => {
    setWords(storageService.getWords());
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetWordInput.trim() || !sentence.trim()) return;
    if (!apiKey) {
        setError("Please set your API Key first.");
        return;
    }

    setIsLoading(true);
    setResult(null);
    setError(null);
    setWarning(null);

    try {
      // Validation Logic
      const matchedWord = words.find(w => w.term.toLowerCase() === targetWordInput.trim().toLowerCase());
      
      if (!matchedWord) {
        setWarning("Word not found in your vocabulary list. AI will check grammar generally.");
      }

      const correction = await geminiService.correctSentence(apiKey, targetWordInput, sentence);
      
      const session: PracticeSession = {
        id: crypto.randomUUID(),
        wordId: matchedWord ? matchedWord.id : 'unknown',
        wordTerm: targetWordInput,
        userSentence: sentence,
        correctedSentence: correction.corrected_sentence,
        betterVersion: correction.better_version,
        feedback: correction.feedback,
        isCorrect: correction.is_correct,
        createdAt: Date.now(),
      };

      // Only save to history if it was a real word? Or always? Prompt implies history log is needed.
      storageService.addPracticeSession(session);
      setResult(session);
    } catch (err: any) {
      setError(err.message || "Failed to analyze sentence.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-slate-800">Sentence Practice</h2>
        <p className="text-slate-500">Master your vocabulary by using it in context.</p>
      </div>

      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <form onSubmit={handleSubmit} className="space-y-6">
          
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Target Word</label>
            <input 
              type="text"
              value={targetWordInput}
              onChange={(e) => setTargetWordInput(e.target.value)}
              placeholder="e.g. Ephemeral"
              className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Your Sentence</label>
            <textarea
              value={sentence}
              onChange={(e) => setSentence(e.target.value)}
              placeholder={`Write a sentence using "${targetWordInput || 'the word'}"...`}
              className="w-full p-4 h-32 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none resize-none transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !targetWordInput.trim() || !sentence.trim()}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors flex justify-center items-center gap-2"
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            Check Sentence
          </button>
        </form>
        
        {warning && (
          <div className="mt-4 p-3 bg-amber-50 text-amber-700 rounded-lg flex items-center gap-2 text-sm border border-amber-100">
             <AlertTriangle className="w-4 h-4" /> {warning}
          </div>
        )}

        {error && (
            <div className="mt-4 text-red-600 bg-red-50 p-3 rounded-lg text-sm text-center border border-red-100">
                {error}
            </div>
        )}
      </div>

      {result && (
        <div className="animate-in fade-in slide-in-from-bottom-6 space-y-6">
            {/* Status Header */}
            <div className={`p-4 rounded-xl flex items-center gap-3 border ${result.isCorrect ? 'bg-green-50 border-green-100 text-green-700' : 'bg-amber-50 border-amber-100 text-amber-700'}`}>
                {result.isCorrect ? <Check className="w-6 h-6" /> : <X className="w-6 h-6" />}
                <span className="font-semibold text-lg">{result.isCorrect ? 'Great Job!' : 'Needs Improvement'}</span>
            </div>

            {/* Comparison Cards */}
            <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                    <h4 className="text-xs font-bold text-slate-400 uppercase mb-2">Your Attempt</h4>
                    <p className="text-slate-800">{result.userSentence}</p>
                </div>
                <div className="bg-white p-5 rounded-xl border border-indigo-100 shadow-sm ring-1 ring-indigo-50">
                    <h4 className="text-xs font-bold text-indigo-400 uppercase mb-2 flex items-center gap-1">
                        <Sparkles className="w-3 h-3" /> Better Version
                    </h4>
                    <p className="text-indigo-900 font-medium">{result.betterVersion}</p>
                </div>
            </div>

            {/* Feedback */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h4 className="text-sm font-bold text-slate-700 mb-3 flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-slate-400" /> 
                    AI Feedback
                </h4>
                <p className="text-slate-600 leading-relaxed">{result.feedback}</p>
                
                {!result.isCorrect && result.correctedSentence !== result.userSentence && (
                    <div className="mt-4 pt-4 border-t border-slate-100">
                        <span className="text-xs text-slate-400 uppercase font-bold">Correction: </span>
                        <span className="text-slate-700 ml-2">{result.correctedSentence}</span>
                    </div>
                )}
            </div>
        </div>
      )}
    </div>
  );
};

export default Practice;
