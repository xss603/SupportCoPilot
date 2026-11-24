import pg from 'pg';
import { config } from '../config.js';

export interface TelemetryRecord {
  projectId: string | number;
  issueIid: number;
  title: string;
  category: string;
  confidence: number;
  platformRequestId?: string | null;
  status: 'auto-resolved' | 'needs-human-review';
  executionTimeMs: number;
}

export class TelemetryLogger {
  private pool: pg.Pool | null = null;

  constructor() {
    if (config.DATABASE_URL) {
      this.pool = new pg.Pool({ connectionString: config.DATABASE_URL });
      this.initDb();
    }
  }

  private async initDb(): Promise<void> {
    if (!this.pool) return;
    try {
      await this.pool.query(`
        CREATE TABLE IF NOT EXISTS public.gitlab_issue_telemetry (
          id SERIAL PRIMARY KEY,
          project_id VARCHAR(100),
          issue_iid INT NOT NULL,
          title VARCHAR(500) NOT NULL,
          category VARCHAR(50) NOT NULL,
          confidence NUMERIC(3, 2) NOT NULL,
          platform_request_id VARCHAR(100),
          status VARCHAR(50) NOT NULL,
          execution_time_ms INT,
          created_at TIMESTAMPTZ DEFAULT NOW()
        );
      `);
    } catch (err) {
      console.warn('Failed to initialize telemetry database table:', err);
    }
  }

  async record(record: TelemetryRecord): Promise<void> {
    console.log(
      `📊 [Telemetry] Project=${record.projectId} Issue=#${record.issueIid} Category=${record.category} ` +
      `Confidence=${(record.confidence * 100).toFixed(0)}% Status=${record.status} Time=${record.executionTimeMs}ms`
    );

    if (this.pool) {
      try {
        await this.pool.query(
          `INSERT INTO public.gitlab_issue_telemetry 
           (project_id, issue_iid, title, category, confidence, platform_request_id, status, execution_time_ms)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
          [
            String(record.projectId),
            record.issueIid,
            record.title.slice(0, 500),
            record.category,
            record.confidence,
            record.platformRequestId || null,
            record.status,
            record.executionTimeMs,
          ]
        );
      } catch (err) {
        console.warn('Failed to insert telemetry record into database:', err);
      }
    }
  }
}

export const telemetry = new TelemetryLogger();
