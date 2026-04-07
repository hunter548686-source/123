export type TaskItem = {
  id: number;
  projectId: number;
  userId: number;
  taskType: string;
  templateId: string;
  strategy: "cheap" | "stable" | "urgent";
  status: string;
  workflowStage: string;
  planningStatus: string;
  executionStatus: string;
  reviewStatus: string;
  executionMode: string;
  quotedPrice?: number | null;
  finalCost?: number | null;
  finalCharge?: number | null;
  selectedProvider?: string | null;
  selectedGpuType?: string | null;
  retryLimit: number;
  retryCount: number;
  progress: number;
  lastError?: string | null;
  planSummary?: string | null;
  executionBrief?: string | null;
  codingInstructions?: string | null;
  reviewSummary?: string | null;
  latestFixInstructions?: string | null;
  resultSummary?: string | null;
  reviewRound?: number;
  reviewApproved?: boolean | null;
  createdAt: string;
  updatedAt: string;
};

export type TaskRun = {
  id: number;
  attemptNo: number;
  provider: string;
  gpuType: string;
  region?: string | null;
  runtimeTarget: string;
  status: string;
  runtimeSeconds: number;
  providerCost: number;
  schedulerScore?: number | null;
  failReason?: string | null;
  localExecutorNote?: string | null;
  startedAt?: string | null;
  endedAt?: string | null;
  createdAt: string;
};

export type TaskEvent = {
  id: number;
  source: string;
  stage: string;
  level: string;
  message: string;
  detailPayload?: Record<string, unknown> | null;
  createdAt: string;
};

export type ArtifactItem = {
  id: number;
  type: string;
  storagePath: string;
  downloadUrl?: string | null;
  fileSize: number;
  checksum?: string | null;
  metadataPayload?: Record<string, unknown> | null;
  createdAt: string;
};

export type WalletData = {
  id: number;
  balance: number;
  frozenBalance: number;
  currency: string;
  createdAt: string;
};

export type WalletLedgerItem = {
  id: number;
  type: string;
  amount: number;
  balanceAfter: number;
  refType?: string | null;
  refId?: string | null;
  createdAt: string;
};

export type ProviderOffer = {
  provider: string;
  gpuType: string;
  region?: string | null;
  pricePerHour: number;
  reliabilityScore: number;
  startupScore: number;
  successRate: number;
  score?: number;
  estimatedPrice?: number;
  estimatedRuntimeMinutes?: number;
};

export type ProviderHealth = {
  provider: string;
  offerCount: number;
  averagePricePerHour: number;
  averageReliability: number;
  averageStartupScore: number;
  averageSuccessRate: number;
};

export type BillingSnapshot = {
  revenue: number;
  cost: number;
  grossProfit: number;
  grossMargin: number;
  byProvider: { provider: string; cost: number; runCount: number }[];
};

export type MonitoringOverview = {
  statusBreakdown: Record<string, number>;
  activeRuns: number;
  queuedForRetry: number;
  pendingCleanup: number;
  openCancellations: number;
  recentProviderCost: number;
  recentRuntimeSeconds: number;
  adapterKey: string;
  marketplaceName: string;
  recentFailures: {
    taskId: number;
    status: string;
    provider?: string | null;
    retryCount: number;
    lastError?: string | null;
    updatedAt?: string | null;
  }[];
};

export type HomeMetrics = {
  averageDeliverySeconds: number;
  successRate7d: number;
  providerCount: number;
  costVisibilityCoverage: number;
  sampleSize7d: number;
  completedTasks7d: number;
  updatedAt: string;
};

export type AdminTaskBundle = {
  items: TaskItem[];
  summary: {
    total: number;
    running: number;
    failed: number;
    completed: number;
  };
};

export type AdminUserOverview = {
  id: number;
  email: string;
  role: string;
  status: string;
  walletBalance: number;
  frozenBalance: number;
  totalTasks: number;
  runningTasks: number;
  completedTasks: number;
  failedTasks: number;
  createdAt: string;
};

export type CodeEditHistoryItem = {
  id: number;
  taskId?: number | null;
  reviewChainId?: number | null;
  actorUserId?: number | null;
  actorEmail?: string | null;
  chainStepNo?: number | null;
  reviewChainStatus?: string | null;
  workflowStage?: string | null;
  reviewRound?: number | null;
  reviewApproved?: boolean | null;
  status: string;
  summary?: string | null;
  instructions: string;
  requestedFiles: string[];
  changedFiles: string[];
  operationsCount: number;
  diffPreview?: string | null;
  testCommands: string[];
  testResults: { command: string; returncode: number; stdout: string; stderr: string }[];
  modelMode?: string | null;
  rawModelNote?: string | null;
  rollbackStatus: string;
  rollbackError?: string | null;
  rollbackActorUserId?: number | null;
  rollbackActorEmail?: string | null;
  rolledBackAt?: string | null;
  createdAt: string;
  updatedAt: string;
  files: { id: number; path: string; createdAt: string }[];
};

export type CodeEditReviewChainItem = {
  id: number;
  taskId: number;
  status: string;
  startedReviewRound: number;
  currentReviewRound: number;
  totalExecutions: number;
  latestReviewSummary?: string | null;
  latestFixInstructions?: string | null;
  finalReviewApproved?: boolean | null;
  finalReviewSummary?: string | null;
  openedAt: string;
  closedAt?: string | null;
  createdAt: string;
  updatedAt: string;
};

export const MOCK_TASKS: TaskItem[] = [
  {
    id: 1024,
    projectId: 1,
    userId: 1,
    taskType: "text_to_video",
    templateId: "wanx-v1",
    strategy: "cheap",
    status: "completed",
    workflowStage: "done",
    planningStatus: "completed",
    executionStatus: "completed",
    reviewStatus: "completed",
    executionMode: "hybrid",
    quotedPrice: 14.92,
    finalCost: 10.74,
    finalCharge: 14.92,
    selectedProvider: "runpod",
    selectedGpuType: "RTX 4090",
    retryLimit: 2,
    retryCount: 1,
    progress: 100,
    planSummary: "由 GPT-5.4 完成任务规划，首轮尝试 Vast.ai，失败后迁移 Runpod。",
    reviewSummary: "由 GPT-5.4 审查通过，可交付。",
    resultSummary: "城市夜景广告片已生成并归档。",
    createdAt: "2026-04-06T20:14:00+08:00",
    updatedAt: "2026-04-06T20:28:00+08:00",
  },
  {
    id: 1025,
    projectId: 1,
    userId: 1,
    taskType: "image_to_video",
    templateId: "frame-flow",
    strategy: "stable",
    status: "running",
    workflowStage: "execution",
    planningStatus: "completed",
    executionStatus: "in_progress",
    reviewStatus: "pending",
    executionMode: "hybrid",
    quotedPrice: 18.6,
    selectedProvider: "runpod",
    selectedGpuType: "A100 80GB",
    retryLimit: 2,
    retryCount: 0,
    progress: 68,
    planSummary: "已确认高稳定策略，优先稳定供给池。",
    resultSummary: "正在生成中间帧与审查包。",
    createdAt: "2026-04-06T21:03:00+08:00",
    updatedAt: "2026-04-06T21:11:00+08:00",
  },
];

export const MOCK_TASK_DETAIL = {
  task: MOCK_TASKS[0],
  runs: [
    {
      id: 1,
      attemptNo: 2,
      provider: "runpod",
      gpuType: "RTX 4090",
      region: "us-central",
      runtimeTarget: "hybrid",
      status: "finished",
      runtimeSeconds: 720,
      providerCost: 10.74,
      schedulerScore: 0.87,
      localExecutorNote: "WSL + Ollama 完成 prompt 预处理和执行摘要对齐。",
      startedAt: "2026-04-06T20:20:00+08:00",
      endedAt: "2026-04-06T20:28:00+08:00",
      createdAt: "2026-04-06T20:20:00+08:00",
    },
    {
      id: 2,
      attemptNo: 1,
      provider: "vast.ai",
      gpuType: "RTX 4090",
      region: "us-west",
      runtimeTarget: "hybrid",
      status: "error",
      runtimeSeconds: 180,
      providerCost: 0.12,
      schedulerScore: 0.81,
      failReason: "provider interrupted before artifact upload",
      localExecutorNote: "已生成重试所需 checkpoint 摘要。",
      startedAt: "2026-04-06T20:15:00+08:00",
      endedAt: "2026-04-06T20:18:00+08:00",
      createdAt: "2026-04-06T20:15:00+08:00",
    },
  ] satisfies TaskRun[],
  events: [
    {
      id: 1,
      source: "planner",
      stage: "planning",
      level: "success",
      message: "GPT-5.4 完成执行摘要，确认先便宜后兜底。",
      createdAt: "2026-04-06T20:14:20+08:00",
    },
    {
      id: 2,
      source: "scheduler",
      stage: "execution",
      level: "error",
      message: "Vast.ai 首轮中断，自动迁移 Runpod。",
      createdAt: "2026-04-06T20:18:09+08:00",
    },
    {
      id: 3,
      source: "reviewer",
      stage: "review",
      level: "success",
      message: "审查完成，结果可交付。",
      createdAt: "2026-04-06T20:28:18+08:00",
    },
  ] satisfies TaskEvent[],
  artifacts: [
    {
      id: 1,
      type: "video",
      storagePath: "/artifacts/task-1024/result.mp4",
      downloadUrl: "https://download.example.com/task-1024.mp4",
      fileSize: 24_000_000,
      checksum: "sha256:mock-1024",
      metadataPayload: { source: "mock" },
      createdAt: "2026-04-06T20:28:21+08:00",
    },
  ] satisfies ArtifactItem[],
  codeEdits: [
    {
      id: 11,
      taskId: 1024,
      reviewChainId: 3,
      actorUserId: 1,
      actorEmail: "admin@example.com",
      chainStepNo: 1,
      reviewChainStatus: "approved",
      workflowStage: "review",
      reviewRound: 1,
      reviewApproved: true,
      status: "applied",
      summary: "补充交付摘要与失败恢复说明",
      instructions: "补充更稳定的交付摘要，并保留失败恢复说明。",
      requestedFiles: ["apps/api/app/services/gpt_workflow.py"],
      changedFiles: ["apps/api/app/services/gpt_workflow.py"],
      operationsCount: 1,
      diffPreview: "--- sample\n+++ sample\n@@\n-old\n+new",
      testCommands: ["python -m pytest .\\apps\\api\\tests"],
      testResults: [{ command: "python -m pytest .\\apps\\api\\tests", returncode: 0, stdout: "ok", stderr: "" }],
      modelMode: "qwen2.5-coder:7b",
      rawModelNote: "{}",
      rollbackStatus: "available",
      createdAt: "2026-04-06T20:24:00+08:00",
      updatedAt: "2026-04-06T20:24:00+08:00",
      files: [
        {
          id: 1,
          path: "apps/api/app/services/gpt_workflow.py",
          createdAt: "2026-04-06T20:24:00+08:00",
        },
      ],
    },
  ] satisfies CodeEditHistoryItem[],
  codeEditChains: [
    {
      id: 3,
      taskId: 1024,
      status: "approved",
      startedReviewRound: 0,
      currentReviewRound: 1,
      totalExecutions: 1,
      latestReviewSummary: "审查通过，交付稳定。",
      latestFixInstructions: "",
      finalReviewApproved: true,
      finalReviewSummary: "最终审查通过。",
      openedAt: "2026-04-06T20:23:00+08:00",
      closedAt: "2026-04-06T20:28:00+08:00",
      createdAt: "2026-04-06T20:23:00+08:00",
      updatedAt: "2026-04-06T20:28:00+08:00",
    },
  ] satisfies CodeEditReviewChainItem[],
};

export const MOCK_WALLET: WalletData = {
  id: 1,
  balance: 328.4,
  frozenBalance: 36,
  currency: "CNY",
  createdAt: "2026-04-06T10:00:00+08:00",
};

export const MOCK_LEDGER: WalletLedgerItem[] = [
  {
    id: 1,
    type: "consume",
    amount: 14.92,
    balanceAfter: 328.4,
    refType: "task",
    refId: "1024",
    createdAt: "2026-04-06T20:28:22+08:00",
  },
  {
    id: 2,
    type: "recharge",
    amount: 200,
    balanceAfter: 343.32,
    refType: "manual",
    refId: "bank",
    createdAt: "2026-04-06T18:00:00+08:00",
  },
];

export const MOCK_OFFERS: ProviderOffer[] = [
  {
    provider: "vast.ai",
    gpuType: "RTX 4090",
    region: "us-west",
    pricePerHour: 0.3,
    reliabilityScore: 0.68,
    startupScore: 0.76,
    successRate: 0.73,
    score: 0.81,
    estimatedPrice: 14.92,
    estimatedRuntimeMinutes: 12,
  },
  {
    provider: "runpod",
    gpuType: "RTX 4090",
    region: "us-central",
    pricePerHour: 0.59,
    reliabilityScore: 0.93,
    startupScore: 0.88,
    successRate: 0.95,
    score: 0.87,
    estimatedPrice: 18.6,
    estimatedRuntimeMinutes: 12,
  },
  {
    provider: "io.net",
    gpuType: "RTX 4090",
    region: "ap-southeast",
    pricePerHour: 0.41,
    reliabilityScore: 0.79,
    startupScore: 0.71,
    successRate: 0.82,
    score: 0.78,
    estimatedPrice: 16.1,
    estimatedRuntimeMinutes: 12,
  },
];

export const MOCK_PROVIDER_HEALTH: ProviderHealth[] = [
  {
    provider: "runpod",
    offerCount: 2,
    averagePricePerHour: 0.99,
    averageReliability: 0.945,
    averageStartupScore: 0.855,
    averageSuccessRate: 0.96,
  },
  {
    provider: "vast.ai",
    offerCount: 1,
    averagePricePerHour: 0.3,
    averageReliability: 0.68,
    averageStartupScore: 0.76,
    averageSuccessRate: 0.73,
  },
  {
    provider: "io.net",
    offerCount: 1,
    averagePricePerHour: 0.41,
    averageReliability: 0.79,
    averageStartupScore: 0.71,
    averageSuccessRate: 0.82,
  },
];

export const MOCK_BILLING: BillingSnapshot = {
  revenue: 246.8,
  cost: 174.2,
  grossProfit: 72.6,
  grossMargin: 29.42,
  byProvider: [
    { provider: "runpod", cost: 92.6, runCount: 11 },
    { provider: "vast.ai", cost: 51.2, runCount: 15 },
    { provider: "io.net", cost: 30.4, runCount: 6 },
  ],
};

export const MOCK_HOME_METRICS: HomeMetrics = {
  averageDeliverySeconds: 520,
  successRate7d: 97.6,
  providerCount: 3,
  costVisibilityCoverage: 100,
  sampleSize7d: 42,
  completedTasks7d: 41,
  updatedAt: "2026-04-08T01:12:00+08:00",
};

export const MOCK_ADMIN_USERS: AdminUserOverview[] = [
  {
    id: 1,
    email: "owner@example.com",
    role: "admin",
    status: "active",
    walletBalance: 328.4,
    frozenBalance: 36,
    totalTasks: 2,
    runningTasks: 1,
    completedTasks: 1,
    failedTasks: 0,
    createdAt: "2026-04-06T10:00:00+08:00",
  },
];
