"use client";

import React from "react";

function renderInlineFormatting(text: string): React.ReactNode[] {
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return tokens.map((token, idx) => {
    if (token.startsWith("**") && token.endsWith("**") && token.length > 4) {
      return (
        <strong key={idx} className="font-semibold">
          {token.slice(2, -2)}
        </strong>
      );
    }
    if (token.startsWith("`") && token.endsWith("`") && token.length > 2) {
      return (
        <code
          key={idx}
          className="rounded bg-[var(--background)] px-1 py-0.5 text-[11px] font-mono"
        >
          {token.slice(1, -1)}
        </code>
      );
    }
    return <React.Fragment key={idx}>{token}</React.Fragment>;
  });
}

/**
 * Lightweight safe chat formatter supporting bold text, inline code, bullet lists,
 * and Markdown pipe tables without raw HTML injection.
 */
export function FormattedChatText({ content }: { content: string }) {
  const lines = content.split("\n");
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i].trimEnd();

    // Detect Markdown pipe table block
    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      const tableLines: string[] = [];
      while (
        i < lines.length &&
        lines[i].trim().startsWith("|") &&
        lines[i].trim().endsWith("|")
      ) {
        tableLines.push(lines[i].trim());
        i += 1;
      }
      const cleanRows = tableLines
        .filter((row) => Boolean(row.replace(/[\s|:-]/g, "")))
        .map((row) =>
          row
            .slice(1, -1)
            .split("|")
            .map((cell) => cell.trim())
        );

      if (cleanRows.length >= 2) {
        const [header, ...body] = cleanRows;
        blocks.push(
          <div key={`tbl-${i}`} className="my-2 overflow-x-auto rounded-lg border border-[var(--border)]">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-[var(--background)] text-[var(--muted-foreground)]">
                <tr>
                  {header.map((col, cIdx) => (
                    <th key={cIdx} className="px-2.5 py-1.5 font-semibold whitespace-nowrap">
                      {renderInlineFormatting(col)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {body.map((row, rIdx) => (
                  <tr key={rIdx} className="bg-[var(--surface)]/60">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="px-2.5 py-1.5 whitespace-nowrap">
                        {renderInlineFormatting(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
      if (cleanRows.length === 1) {
        blocks.push(
          <p key={`p-${i}`} className="leading-relaxed">
            {renderInlineFormatting(cleanRows[0].join(" · "))}
          </p>
        );
        continue;
      }
    }

    // Bullet or numbered list block
    if (/^[-*]\s+/.test(line.trim()) || /^\d+\.\s+/.test(line.trim())) {
      const items: string[] = [];
      while (
        i < lines.length &&
        (/^[-*]\s+/.test(lines[i].trim()) || /^\d+\.\s+/.test(lines[i].trim()))
      ) {
        items.push(lines[i].trim().replace(/^([-*]|\d+\.)\s+/, ""));
        i += 1;
      }
      blocks.push(
        <ul key={`ul-${i}`} className="my-1.5 space-y-1 pl-4 list-disc">
          {items.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
              {renderInlineFormatting(item)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    if (line.trim() === "---") {
      i += 1;
      continue;
    }

    if (!line.trim()) {
      i += 1;
      continue;
    }

    blocks.push(
      <p key={`p-${i}`} className="leading-relaxed">
        {renderInlineFormatting(line)}
      </p>
    );
    i += 1;
  }

  return <div className="space-y-1.5">{blocks}</div>;
}
