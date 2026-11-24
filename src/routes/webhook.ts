import { Request, Response, Router } from 'express';
import { config } from '../config.js';
import { orchestrator } from '../services/orchestrator.js';
import { GitLabIssue } from '../mcp/gitlabClient.js';

export const webhookRouter: Router = Router();

webhookRouter.post('/gitlab', async (req: Request, res: Response): Promise<void> => {
  // 1. Verify token if configured
  if (config.WEBHOOK_SECRET) {
    const tokenHeader = req.header('X-Gitlab-Token');
    if (tokenHeader !== config.WEBHOOK_SECRET) {
      console.warn('⚠️ Webhook rejected: Invalid X-Gitlab-Token header');
      res.status(401).json({ error: 'Unauthorized webhook secret' });
      return;
    }
  }

  const payload = req.body;
  const event = req.header('X-Gitlab-Event');

  // We are only interested in Issue Hook events
  if (payload.object_kind !== 'issue' && event !== 'Issue Hook') {
    res.status(200).json({ status: 'ignored', message: 'Not an issue event' });
    return;
  }

  const action = payload.object_attributes?.action;
  if (!['open', 'reopen'].includes(action)) {
    res.status(200).json({ status: 'ignored', message: `Ignored action: ${action}` });
    return;
  }

  // Acknowledge webhook immediately so GitLab does not timeout
  res.status(202).json({ status: 'accepted', issue_iid: payload.object_attributes?.iid });

  // Map GitLab webhook payload into standard GitLabIssue model
  const issue: GitLabIssue = {
    id: payload.object_attributes.id,
    iid: payload.object_attributes.iid,
    project_id: payload.project.id,
    title: payload.object_attributes.title,
    description: payload.object_attributes.description || '',
    state: payload.object_attributes.state,
    labels: (payload.labels || []).map((l: any) => (typeof l === 'string' ? l : l.title)),
    author: {
      id: payload.user.id,
      username: payload.user.username,
      name: payload.user.name,
    },
    web_url: payload.object_attributes.url,
    created_at: payload.object_attributes.created_at,
  };

  // Process asynchronously
  setImmediate(async () => {
    try {
      await orchestrator.processIssue(issue);
    } catch (err: any) {
      console.error(`❌ [Webhook Error] Failed processing Issue #${issue.iid}:`, err.message);
    }
  });
});
