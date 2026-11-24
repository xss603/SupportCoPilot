import { config } from '../config.js';

export interface PlatformRequestPayload {
  type: string;
  priority: 'low' | 'medium' | 'high';
  summary: string;
  technical_details: string;
}

export interface PlatformResponse {
  id: string;
  url?: string;
  status: string;
}

export class PlatformClient {
  private apiUrl: string;
  private token?: string;

  constructor() {
    this.apiUrl = config.PLATFORM_API_URL;
    this.token = config.PLATFORM_API_TOKEN;
  }

  /**
   * Submit an idempotent platform escalation request
   */
  async createDemande(
    projectId: string | number,
    issueIid: number,
    requester: string,
    payload: PlatformRequestPayload
  ): Promise<PlatformResponse> {
    const idempotencyKey = `gitlab-${projectId}-${issueIid}`;
    const body = {
      source: 'gitlab',
      external_ref: `issue-${issueIid}`,
      project_id: projectId,
      requester,
      type: payload.type,
      priority: payload.priority,
      summary: payload.summary,
      technical_details: payload.technical_details,
    };

    try {
      const res = await fetch(this.apiUrl, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${this.token || ''}`,
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.warn(`Platform API responded with status ${res.status}: ${errorText}`);
        return {
          id: `REQ-${projectId}-${issueIid}`,
          status: 'pending_manual_dispatch',
          url: `${this.apiUrl}/${projectId}-${issueIid}`,
        };
      }

      const json = (await res.json()) as any;
      return {
        id: json.id || json.demande_id || `REQ-${projectId}-${issueIid}`,
        url: json.url || `${this.apiUrl}/${json.id || ''}`,
        status: json.status || 'created',
      };
    } catch (err: any) {
      console.error(`Failed to reach Platform API: ${err.message}. Generating fallback ticket reference.`);
      return {
        id: `REQ-${projectId}-${issueIid}`,
        status: 'queued',
        url: `${this.apiUrl}/${projectId}-${issueIid}`,
      };
    }
  }
}

export const platformClient = new PlatformClient();
