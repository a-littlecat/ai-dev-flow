/**
 * Chinese display labels for every wire enum. Status is always conveyed with
 * text (and a text/unicode symbol), never by colour alone (WCAG 2.2 1.4.1).
 */

export const LIFECYCLE_LABEL: Record<string, string> = {
  Draft: "草稿",
  Ready: "就绪",
  "In Progress": "进行中",
  Blocked: "已阻塞",
  Review: "待评审",
  "Needs Fix": "需修复",
  Accepted: "已验收",
  Closed: "已关闭",
  Deferred: "已延后",
  Cancelled: "已取消",
};

export const REVIEW_LABEL: Record<string, string> = {
  Pending: "待评审",
  "In Review": "评审中",
  Passed: "评审通过",
  "Needs Fix": "需修复",
  "Do Not Merge": "禁止合并",
};

export const REVIEW_REQUIREMENT_LABEL: Record<string, string> = {
  "Legacy Unspecified": "旧合同未声明（沿用强制门禁）",
  Required: "必须独立评审",
  "Not Required": "不强制评审",
};

export const REVIEW_STATE_LABEL: Record<string, string> = {
  "Not Run": "未运行",
  "In Review": "评审中",
  Passed: "评审通过",
  "Needs Fix": "需修复",
  Blocked: "已阻塞",
};

export const UA_STATUS_LABEL: Record<string, string> = {
  "Not Required": "无需验收",
  Pending: "待用户验收",
  Passed: "验收通过",
  Failed: "验收失败",
  Deferred: "验收延后",
  TBD: "待定",
};

export const ACCEPTANCE_LABEL: Record<string, string> = {
  None: "无验收授权",
  "User Confirmed": "用户已确认",
  "Designated Acceptor Confirmed": "指定验收人已确认",
};

export const COMMIT_LABEL: Record<string, string> = {
  "Not Applicable": "不适用",
  Uncommitted: "未提交",
  Committed: "已提交",
};

export const MERGE_LABEL: Record<string, string> = {
  "Not Applicable": "不适用",
  Unmerged: "未合并",
  Merged: "已合并",
  Deferred: "延后合并",
};

export const MERGE_AUTHORITY_LABEL: Record<string, string> = {
  None: "无合并授权",
  "User Authorized": "用户已授权合并",
  Denied: "合并被拒绝",
};

export const CLOSE_AUTHORITY_LABEL: Record<string, string> = {
  None: "无关闭授权",
  "User Authorized": "用户已授权关闭",
  "Rule Authorized": "规则授权关闭",
  Denied: "关闭被拒绝",
};

export const ACTION_KIND_LABEL: Record<string, string> = {
  plan: "规划",
  execute: "执行",
  continue: "继续",
  review: "评审",
  repair: "修复",
  user_decision: "用户决定",
  commit: "提交",
  merge: "合并",
  release: "发布",
  close: "关闭",
  none: "无动作",
};

export const ELIGIBILITY_LABEL: Record<string, string> = {
  actionable: "可执行",
  blocked: "被阻塞",
  needs_authority: "需要授权",
  unknown: "未知",
  not_applicable: "不适用",
};

export const AUTHORITY_STATE_LABEL: Record<string, string> = {
  not_required: "无需授权",
  present: "已授权",
  missing: "缺少授权",
  denied: "已拒绝",
  unsupported: "不支持",
  unknown: "未知",
};

export const REQUIRED_AUTHORITY_LABEL: Record<string, string> = {
  none: "无",
  execution: "执行授权",
  review: "评审授权",
  repair: "修复授权",
  commit: "提交授权",
  merge: "合并授权",
  release: "发布授权",
  close: "关闭授权",
  user_decision: "用户决定",
};

export const ACTION_REASON_LABEL: Record<string, string> = {
  CONTRACT_STATE_INVALID: "合同状态非法",
  TERMINAL_STATE: "终态",
  REPAIR_AUTHORITY_UNSUPPORTED: "不支持修复授权",
  PLANNING_DECISION_REQUIRED: "需要规划决定",
  DEPENDENCY_STATE_UNKNOWN: "依赖状态未知",
  DEPENDENCY_UNSATISFIED: "依赖未满足",
  EXECUTION_AUTHORITY_UNSUPPORTED: "无执行授权依据",
  CONTINUE_AUTHORITY_UNSUPPORTED: "无继续授权依据",
  REVIEW_AUTHORITY_UNSUPPORTED: "无评审授权依据",
  USER_DECISION_PENDING: "等待用户决定",
  ACCEPTANCE_RECORD_PENDING: "等待验收记录",
  COMMIT_AUTHORITY_UNSUPPORTED: "无提交授权依据",
  MERGE_AUTHORITY_PRESENT: "合并授权存在",
  MERGE_AUTHORITY_DENIED: "合并授权被拒",
  MERGE_AUTHORITY_REQUIRED: "需要合并授权",
  RELEASE_AXIS_UNSUPPORTED: "发布轴不受支持",
  CLOSE_AUTHORITY_PRESENT: "关闭授权存在",
  CLOSE_AUTHORITY_DENIED: "关闭授权被拒",
  CLOSE_AUTHORITY_REQUIRED: "需要关闭授权",
  STATE_COMBINATION_UNMAPPED: "状态组合未映射",
};

export const PARALLEL_RESULT_LABEL: Record<string, string> = {
  candidate: "并行候选（需用户确认，非授权）",
  must_serial: "必须串行",
  unknown: "并行未知",
};

/** Short on-graph forms of PARALLEL_RESULT_LABEL (full text stays in tooltips/lists). */
export const PARALLEL_RESULT_SHORT: Record<string, string> = {
  candidate: "并行候选",
  must_serial: "必须串行",
  unknown: "并行未知",
};

export const PARALLEL_REASON_LABEL: Record<string, string> = {
  DEPENDENCY_PATH_PRESENT: "存在依赖路径",
  EXPLICIT_CONFLICT: "显式冲突",
  WRITE_SCOPE_OVERLAP: "写范围重叠",
  MODULE_LOCK_OVERLAP: "模块锁重叠",
  SHARED_HIGH_RISK_SURFACE: "共享高风险面",
  HIGH_RISK_SERIAL: "高风险须串行",
  UA_LEVEL_SERIAL: "高 UA 等级须串行",
  WORKTREE_EVIDENCE_UNKNOWN: "Worktree 证据未知",
  WORKTREE_SHARED: "共享 Worktree",
  DIRTY_OWNERSHIP_UNKNOWN: "脏文件归属未知",
  PROJECTION_ONLY_CONFLICT: "仅投影文件冲突",
  ALL_CHECKS_PASSED: "全部检查通过",
};

export const EDGE_TYPE_LABEL: Record<string, string> = {
  depends_on: "依赖",
  parent: "父子",
  replaces: "替代",
  discovered_from: "派生",
  conflicts_with: "冲突",
};

export const SEVERITY_LABEL: Record<string, string> = {
  error: "错误",
  violation: "违规",
  warning: "警告",
  info: "信息",
};

export const SEVERITY_ICON: Record<string, string> = {
  error: "✖",
  violation: "⛔",
  warning: "⚠",
  info: "ℹ",
};

export const FRESHNESS_LABEL: Record<string, string> = {
  fresh: "数据新鲜",
  stale: "数据过期",
  partial: "数据不完整",
};

export const SNAPSHOT_STATE_LABEL: Record<string, string> = {
  fresh: "快照：新鲜",
  stale: "快照：过期",
  partial: "快照：不完整",
};

export const GIT_STATE_LABEL: Record<string, string> = {
  ok: "Git 正常",
  degraded: "Git 降级",
  unavailable: "Git 不可用",
};

export const SCHEDULING_STATE_LABEL: Record<string, string> = {
  canonical: "规范 Scheduling",
  legacy_inferred: "旧格式推断",
  absent: "缺少 Scheduling",
  invalid: "Scheduling 非法",
};

export const PARALLEL_INTENT_LABEL: Record<string, string> = {
  serial: "声明串行",
  consider: "考虑并行",
  unknown: "并行意图未知",
};

export const WORKTREE_REQ_LABEL: Record<string, string> = {
  required: "需要 Worktree",
  optional: "Worktree 可选",
  forbidden: "禁止 Worktree",
  unknown: "Worktree 要求未知",
};

export const CONDITION_EVAL_LABEL: Record<string, string> = {
  satisfied: "已满足",
  unsatisfied: "未满足",
  unknown: "未知",
};

export const AXIS_LABEL: Record<string, string> = {
  lifecycle: "生命周期",
  review_status: "评审",
  ua_status: "用户验收",
  acceptance_authority: "验收授权",
  commit_status: "提交",
  merge_status: "合并",
  merge_authority: "合并授权",
  close_authority: "关闭授权",
};

export const TASK_TYPE_LABEL: Record<string, string> = {
  document: "文档",
  plan: "规划",
  code: "代码",
  review: "评审",
  repair: "修复",
  test: "测试",
};

export function label(map: Record<string, string>, value: string | null): string {
  if (value === null) {
    return "未知";
  }
  return map[value] ?? value;
}

export function shortSha(sha: string | null, length = 7): string {
  if (!sha) {
    return "未知";
  }
  return sha.slice(0, length);
}
