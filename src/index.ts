import express from 'express';
import { config } from './config.js';
import { webhookRouter } from './routes/webhook.js';
import { gitlab } from './mcp/gitlabClient.js';
import { orchestrator } from './services/orchestrator.js';

const app = express();
app.use(express.json({ limit: '10mb' }));

// Health check endpoint
app.get('/healthz', (_req, res) => {
  res.json({
    status: 'ok',
    service: 'gitlab-platform-support-daemon',
    timestamp: new Date().toISOString(),
    config: {
      gitlabUrl: config.GITLAB_URL,
      model: config.GEMINI_MODEL,
      confidenceThreshold: config.CONFIDENCE_THRESHOLD,
      pollingEnabled: config.ENABLE_POLLING,
    },
  });
});

// Register Webhook Router
app.use('/webhook', webhookRouter);

// Start background poller if enabled and project ID is configured
function startPollingLoop() {
  if (!config.ENABLE_POLLING) {
    console.log('⏸️ Background polling is disabled.');
    return;
  }

  const projectIds = config.GITLAB_PROJECT_ID
    ? config.GITLAB_PROJECT_ID.split(',').map(id => id.trim()).filter(Boolean)
    : [];

  if (projectIds.length === 0) {
    console.log('ℹ️ No GITLAB_PROJECT_ID provided for background polling. Operating in webhook-only mode.');
    return;
  }

  console.log(`⏱️ Starting polling loop every ${config.POLL_INTERVAL_SECONDS}s for projects: ${projectIds.join(', ')}`);

  const poll = async () => {
    for (const projId of projectIds) {
      try {
        const issues = await gitlab.listOpenIssues(projId);
        const untriaged = issues.filter(issue => !gitlab.hasBeenTriaged(issue));

        if (untriaged.length > 0) {
          console.log(`🔎 [Poller] Found ${untriaged.length} untriaged issue(s) in project ${projId}`);
          for (const issue of untriaged) {
            await orchestrator.processIssue(issue);
          }
        }
      } catch (err: any) {
        console.error(`⚠️ [Poller Warning] Error polling project ${projId}:`, err.message);
      }
    }
  };

  // Initial poll on startup
  setTimeout(poll, 3000);

  // Periodic poll
  setInterval(poll, config.POLL_INTERVAL_SECONDS * 1000);
}

// Start HTTP Server
const server = app.listen(config.PORT, config.HOST, () => {
  console.log(`
===========================================================
🚀 GitLab Platform Support Daemon is running!
-----------------------------------------------------------
🌐 Host/Port:     http://${config.HOST}:${config.PORT}
🩺 Health Check:  http://${config.HOST}:${config.PORT}/healthz
📥 Webhook URL:   http://${config.HOST}:${config.PORT}/webhook/gitlab
🤖 AI Model:      ${config.GEMINI_MODEL} (Confidence Threshold: ${config.CONFIDENCE_THRESHOLD})
📂 Runbooks Dir:  ./runbooks/
===========================================================
  `);
  startPollingLoop();
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('🛑 SIGTERM received, shutting down gracefully...');
  server.close(() => process.exit(0));
});

process.on('SIGINT', () => {
  console.log('🛑 SIGINT received, shutting down gracefully...');
  server.close(() => process.exit(0));
});
