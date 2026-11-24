import { config } from '../config.js';
import { gitlab, GitLabIssue } from '../mcp/gitlabClient.js';
import { triageEngine } from '../ai/triageEngine.js';
import { runbookSearch } from '../docs/runbookSearch.js';
import { platformClient } from '../platform/platformClient.js';
import { telemetry } from '../telemetry/logger.js';

export class TriageOrchestrator {
  /**
   * Sanitizes issue description by stripping raw images, long stack traces, and HTML
   */
  private sanitizeDescription(raw: string): string {
    if (!raw) return '';
    let text = raw;
    // Strip markdown images ![alt](url)
    text = text.replace(/!\[.*?\]\(.*?\)/g, '');
    // Strip code fences over 1000 characters
    text = text.replace(/```[\s\S]*?```/g, match => {
      if (match.length > 800) {
        return match.slice(0, 800) + '\n... [Remaining log lines truncated for AI prompt]```';
      }
      return match;
    });
    // Strip raw HTML
    text = text.replace(/<[^>]*>/g, ' ');
    // Hard limit at 2,500 characters
    if (text.length > 2500) {
      text = text.slice(0, 2500) + '... [Description truncated]';
    }
    return text.trim();
  }

  /**
   * Process and triage a single GitLab issue
   */
  async processIssue(issue: GitLabIssue): Promise<void> {
    const startTime = Date.now();
    const projectId = issue.project_id;
    const issueIid = issue.iid;

    console.log(`\n🔍 [Orchestrator] Evaluating Issue #${issueIid}: "${issue.title}" (Author: @${issue.author.username})`);

    // 1. Guard check: state
    if (issue.state !== 'opened') {
      console.log(`⏩ Issue #${issueIid} is not opened (${issue.state}). Skipping.`);
      return;
    }

    // 2. Guard check: bot loop prevention
    if (issue.author.username === config.GITLAB_BOT_USERNAME) {
      console.log(`⏩ Issue #${issueIid} was created by the support bot. Skipping to prevent loops.`);
      return;
    }

    // 3. Guard check: already triaged
    if (gitlab.hasBeenTriaged(issue)) {
      console.log(`⏩ Issue #${issueIid} already carries 'ai-triaged'. Skipping.`);
      return;
    }

    // 4. Sanitize and retrieve context
    const cleanDesc = this.sanitizeDescription(issue.description);
    const searchQuery = `${issue.title} ${cleanDesc.slice(0, 150)}`;
    const runbookContext = await runbookSearch.searchRelevantContext(searchQuery);

    // 5. Invoke Gemini AI Triage
    console.log(`🤖 [Orchestrator] Invoking Gemini AI for Issue #${issueIid}...`);
    const triage = await triageEngine.triageIssue({
      issueIid,
      title: issue.title,
      description: cleanDesc,
      author: issue.author.username,
      labels: issue.labels,
      runbookContext,
    });

    console.log(`✅ [Orchestrator] AI decision: Category="${triage.category}", Confidence=${triage.confidence}, Escalation=${triage.requires_platform_request}`);

    // 6. Handle Platform API Escalation if needed
    let platformNotice = '';
    let platformRequestId: string | null = null;

    if (triage.requires_platform_request) {
      console.log(`🚀 [Orchestrator] Dispatching platform escalation to /demandes...`);
      const demande = await platformClient.createDemande(
        projectId,
        issueIid,
        issue.author.username,
        triage.platform_request_payload
      );
      platformRequestId = demande.id;
      platformNotice = `\n\n> 📋 **Platform Request Dispatched:** [${demande.id}](${demande.url || '#'})  \n> *Priority:* \`${triage.platform_request_payload.priority}\` | *Type:* \`${triage.platform_request_payload.type}\``;
    }

    // 7. Compose GitLab Comment
    const confidencePct = Math.round(triage.confidence * 100);
    const commentMarkdown = `### 🤖 Platform Support Tier-2 Analysis [Confidence: ${confidencePct}%]

${triage.gitlab_reply_markdown}
${platformNotice}

---
*Classification:* \`${triage.category}\` | *Automated via Platform Support Daemon*`;

    // 8. Post comment to GitLab
    console.log(`💬 [Orchestrator] Posting triage resolution note on Issue #${issueIid}...`);
    await gitlab.createIssueNote(projectId, issueIid, commentMarkdown);

    // 9. Update GitLab labels
    const isHighConfidence = triage.confidence >= config.CONFIDENCE_THRESHOLD;
    const statusLabel = isHighConfidence ? 'auto-resolved' : 'needs-human-review';
    const labelsToAdd = ['ai-triaged', statusLabel, ...(triage.recommended_labels || [])];

    console.log(`🏷️ [Orchestrator] Applying labels to Issue #${issueIid}: ${labelsToAdd.join(', ')}`);
    await gitlab.addLabels(projectId, issueIid, labelsToAdd);

    // 10. Record Telemetry
    const duration = Date.now() - startTime;
    await telemetry.record({
      projectId,
      issueIid,
      title: issue.title,
      category: triage.category,
      confidence: triage.confidence,
      platformRequestId,
      status: statusLabel,
      executionTimeMs: duration,
    });

    console.log(`✨ [Orchestrator] Successfully finished triage for Issue #${issueIid} in ${duration}ms\n`);
  }
}

export const orchestrator = new TriageOrchestrator();
