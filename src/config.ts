import dotenv from 'dotenv';
import { z } from 'zod';

dotenv.config();

const configSchema = z.object({
  // Server Configuration
  PORT: z.coerce.number().default(3000),
  HOST: z.string().default('0.0.0.0'),
  WEBHOOK_SECRET: z.string().optional(),

  // GitLab Configuration
  GITLAB_URL: z.string().url().default('https://gitlab.com'),
  GITLAB_TOKEN: z.string().min(1, 'GITLAB_TOKEN is required for GitLab API/MCP operations'),
  GITLAB_PROJECT_ID: z.string().default(''), // Target project ID or comma-separated list
  GITLAB_BOT_USERNAME: z.string().default('platform-bot'),

  // AI Configuration
  GEMINI_API_KEY: z.string().min(1, 'GEMINI_API_KEY is required for issue triage'),
  GEMINI_MODEL: z.string().default('gemini-2.5-flash'),
  GEMINI_TEMPERATURE: z.coerce.number().default(0.2),
  CONFIDENCE_THRESHOLD: z.coerce.number().default(0.85),

  // Platform API / Backend Escalation
  PLATFORM_API_URL: z.string().url().default('https://api.platform.example.com/v1/demandes'),
  PLATFORM_API_TOKEN: z.string().optional(),

  // Docs API (Optional external RAG)
  DOCS_API_URL: z.string().url().optional(),
  DOCS_API_TOKEN: z.string().optional(),

  // Observability & Database
  DATABASE_URL: z.string().optional(), // PostgreSQL connection string

  // Polling Configuration
  POLL_INTERVAL_SECONDS: z.coerce.number().default(60),
  ENABLE_POLLING: z.enum(['true', 'false']).transform(v => v === 'true').default('true'),
});

export type Config = z.infer<typeof configSchema>;

export function loadConfig(): Config {
  const result = configSchema.safeParse(process.env);
  if (!result.success) {
    console.error('❌ Invalid environment configuration:');
    console.error(result.error.format());
    throw new Error('Configuration validation failed');
  }
  return result.data;
}

export const config = loadConfig();
