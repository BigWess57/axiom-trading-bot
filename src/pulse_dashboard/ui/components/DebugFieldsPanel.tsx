"use client";

import React, { useState } from "react";
import { PulseToken } from "@/lib/types";
import { Copy } from "lucide-react";

interface DebugFieldsPanelProps {
  token: PulseToken;
}

export const DebugFieldsPanel: React.FC<DebugFieldsPanelProps> = ({ token }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Known mapped fields (from decoder.py manual mapping)
  const MAPPED_FIELDS = new Set([
    // Basic Identity
    0, 1, 2, 3, 4, 5, 6, 7,
    // Socials & Info
    9, 10, 11, 46,
    // Holder Analysis  
    13, 14, 15, 16, 17, 28,
    // Financial Metrics
    18, 19, 20, 27,
    // Activity
    23, 24, 25, 29,
    // Timestamps
    30, 34,
    // Dev Info
    33, 41,
    // Social Metrics
    40, 45, 47
  ]);
  
  const getValueColor = (value: any): string => {
    if (value === null || value === undefined) return "text-slate-600";
    if (typeof value === "number") return "text-blue-400";
    if (typeof value === "string") return "text-green-400";
    if (typeof value === "boolean") return "text-purple-400";
    return "text-yellow-400";
  };
  
  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return "null";
    if (typeof value === "string" && value.length > 50) {
      return value.substring(0, 50) + "...";
    }
    return JSON.stringify(value);
  };
  
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };
  
  if (!token.raw_fields) {
    return null;
  }
  
  const fieldEntries = Object.entries(token.raw_fields)
    .sort(([a], [b]) => parseInt(a) - parseInt(b));
  
  return (
    <div className="border-t border-slate-800 mt-2 pt-2">
      <button 
        onClick={() => setIsExpanded(!isExpanded)}
        className="text-xs text-slate-500 hover:text-slate-300 mb-2 flex items-center gap-2"
      >
        <span>{isExpanded ? "▼" : "►"}</span>
        <span>Debug: Raw Fields ({fieldEntries.length})</span>
      </button>
      
      {isExpanded && (
        <div className="grid grid-cols-2 gap-1 text-[10px] font-mono max-h-150 overflow-y-auto bg-slate-950/50 rounded p-2 border border-slate-800">
          {fieldEntries.map(([fieldIndex, value]) => {
            const isMapped = MAPPED_FIELDS.has(parseInt(fieldIndex));
            return (
              <div 
                key={fieldIndex}
                className={`flex gap-2 items-start group `}
                title={isMapped ? "Already mapped in decoder" : "Unmapped field - needs identification"}
                >
            {/* //   ${isMapped ? "opacity-40" : ""} */}
                <span className="text-slate-500 shrink-0">[{fieldIndex}]:</span>
                <span className={`${getValueColor(value)} break-all flex-1`}>
                  {formatValue(value)}
                </span>
                <button
                  onClick={() => copyToClipboard(String(value))}
                  className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                  title="Copy value"
                >
                  <Copy className="w-3 h-3 text-slate-600 hover:text-slate-400" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
