import fs from 'fs';
import path from 'path';
import { config } from '../config.js';

export interface RunbookDoc {
  filename: string;
  title: string;
  content: string;
}

export class RunbookSearcher {
  private runbooksDir: string;
  private cachedRunbooks: RunbookDoc[] = [];

  constructor(runbooksDir = './runbooks') {
    this.runbooksDir = path.resolve(process.cwd(), runbooksDir);
    this.loadRunbooks();
  }

  private loadRunbooks(): void {
    if (!fs.existsSync(this.runbooksDir)) {
      fs.mkdirSync(this.runbooksDir, { recursive: true });
    }

    const files = fs.readdirSync(this.runbooksDir).filter(f => f.endsWith('.md'));
    this.cachedRunbooks = files.map(file => {
      const fullPath = path.join(this.runbooksDir, file);
      const content = fs.readFileSync(fullPath, 'utf8');
      const firstLine = content.split('\n')[0] || file;
      const title = firstLine.replace(/^#+\s*/, '').trim();
      return {
        filename: file,
        title,
        content,
      };
    });
  }

  /**
   * Search local runbooks and optionally external Docs API
   */
  async searchRelevantContext(query: string, maxResults = 3): Promise<string> {
    this.loadRunbooks(); // Refresh on search to pick up dynamic changes

    if (this.cachedRunbooks.length === 0 && !config.DOCS_API_URL) {
      return 'No internal runbooks found in ./runbooks and no DOCS_API_URL configured.';
    }

    const lowerQuery = query.toLowerCase();
    const tokens = lowerQuery
      .split(/[^a-zA-Z0-9_-]+/)
      .filter(t => t.length > 2);

    // Score local runbooks based on token overlaps
    const scored = this.cachedRunbooks.map(doc => {
      let score = 0;
      const docLower = doc.content.toLowerCase();
      const titleLower = doc.title.toLowerCase();

      for (const token of tokens) {
        if (titleLower.includes(token)) score += 5;
        if (docLower.includes(token)) score += 1;
      }
      return { doc, score };
    });

    scored.sort((a, b) => b.score - a.score);
    const topMatches = scored.filter(s => s.score > 0).slice(0, maxResults);

    let context = '';
    if (topMatches.length > 0) {
      context = topMatches
        .map(
          (m, idx) =>
            `### Runbook [${idx + 1}]: ${m.doc.title} (${m.doc.filename})\n${m.doc.content.slice(0, 1500)}`
        )
        .join('\n\n---\n\n');
    }

    // Optionally query external Docs API if configured
    if (config.DOCS_API_URL) {
      try {
        const url = new URL(config.DOCS_API_URL);
        url.searchParams.set('q', query.slice(0, 150));
        const res = await fetch(url.toString(), {
          headers: {
            Authorization: `Bearer ${config.DOCS_API_TOKEN || ''}`,
            Accept: 'application/json',
          },
        });
        if (res.ok) {
          const docsJson = (await res.json()) as any;
          const items = Array.isArray(docsJson) ? docsJson : docsJson.results || docsJson.items || [];
          if (items.length > 0) {
            const externalDocs = items
              .slice(0, 2)
              .map(
                (item: any, i: number) =>
                  `### External Doc [${i + 1}]: ${item.title || 'Doc'}\n${(item.content || item.excerpt || '').slice(0, 800)}`
              )
              .join('\n\n');
            context += `\n\n### External Documentation:\n${externalDocs}`;
          }
        }
      } catch (err) {
        console.warn('Docs API lookup warning:', err);
      }
    }

    return context || 'No matching runbooks found for this issue.';
  }
}

export const runbookSearch = new RunbookSearcher();
