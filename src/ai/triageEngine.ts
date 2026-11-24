import { GoogleGenerativeAI, SchemaType } from '@google/generative-ai';
import { z } from 'zod';
import { config } from '../config.js';
import { buildTriageUserPrompt, SYSTEM_INSTRUCTION, TriageInput } from './promptTemplates.js';

export const triageResultSchema = z.object({
  category: z.enum(['bug', 'how-to', 'access_request', 'configuration', 'other']),
  confidence: z.number().min(0).max(1),
  requires_platform_request: z.boolean(),
  platform_request_payload: z.object({
    type: z.string(),
    priority: z.enum(['low', 'medium', 'high']),
    summary: z.string(),
    technical_details: z.string(),
  }),
  gitlab_reply_markdown: z.string(),
  recommended_labels: z.array(z.string()),
});

export type TriageResult = z.infer<typeof triageResultSchema>;

export class AITriageEngine {
  private genAI: GoogleGenerativeAI;

  constructor() {
    this.genAI = new GoogleGenerativeAI(config.GEMINI_API_KEY);
  }

  async triageIssue(input: TriageInput): Promise<TriageResult> {
    const model = this.genAI.getGenerativeModel({
      model: config.GEMINI_MODEL,
      systemInstruction: SYSTEM_INSTRUCTION,
      generationConfig: {
        temperature: config.GEMINI_TEMPERATURE,
        responseMimeType: 'application/json',
        responseSchema: {
          type: SchemaType.OBJECT,
          properties: {
            category: {
              type: SchemaType.STRING,
              format: 'enum',
              enum: ['bug', 'how-to', 'access_request', 'configuration', 'other'],
            },
            confidence: {
              type: SchemaType.NUMBER,
              description: 'Confidence score from 0.0 to 1.0',
            },
            requires_platform_request: {
              type: SchemaType.BOOLEAN,
              description: 'Whether backend ticket creation (/demandes) is necessary',
            },
            platform_request_payload: {
              type: SchemaType.OBJECT,
              properties: {
                type: { type: SchemaType.STRING },
                priority: {
                  type: SchemaType.STRING,
                  format: 'enum',
                  enum: ['low', 'medium', 'high'],
                },
                summary: { type: SchemaType.STRING },
                technical_details: { type: SchemaType.STRING },
              },
              required: ['type', 'priority', 'summary', 'technical_details'],
            },
            gitlab_reply_markdown: {
              type: SchemaType.STRING,
              description: 'Helpful Markdown response for GitLab developer',
            },
            recommended_labels: {
              type: SchemaType.ARRAY,
              items: { type: SchemaType.STRING },
              description: 'Suggested taxonomy labels',
            },
          },
          required: [
            'category',
            'confidence',
            'requires_platform_request',
            'platform_request_payload',
            'gitlab_reply_markdown',
            'recommended_labels',
          ],
        },
      },
    });

    const userPrompt = buildTriageUserPrompt(input);
    const result = await model.generateContent(userPrompt);
    const responseText = result.response.text();

    const rawJson = JSON.parse(responseText);
    const parsed = triageResultSchema.safeParse(rawJson);

    if (!parsed.success) {
      console.error('Gemini output schema validation error:', parsed.error.format());
      throw new Error(`Invalid structured output from Gemini: ${parsed.error.message}`);
    }

    return parsed.data;
  }
}

export const triageEngine = new AITriageEngine();
