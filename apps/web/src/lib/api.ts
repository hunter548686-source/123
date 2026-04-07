"use client";

import {
  MOCK_BILLING,
  MOCK_LEDGER,
  MOCK_OFFERS,
  MOCK_PROVIDER_HEALTH,
  MOCK_TASK_DETAIL,
  MOCK_TASKS,
  MOCK_WALLET,
  type AdminTaskBundle,
  type AdminUserOverview,
  type BillingSnapshot,
  type CodeEditHistoryItem,
  type CodeEditReviewChainItem,
  type HomeMetrics,
  type MonitoringOverview,
  type ProviderHealth,
  type ProviderOffer,
  type TaskEvent,
  type TaskItem,
  type TaskRun,
  type WalletData,
  type WalletLedgerItem,
} from "./mock";

const TOKEN_KEY = "stablegpu.token";
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

type AuthResult = {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    role: string;
    status: string;
  };
  wallet_balance: string;
};

type TaskDetail = {
  task: TaskItem;
  current_run: TaskRun | null;
  runs: TaskRun[];
  events: TaskEvent[];
  artifacts: {
    id: number;
    type: string;
    storage_path?: string;
    storagePath?: string;
    download_url?: string | null;
    downloadUrl?: string | null;
    file_size?: number;
    fileSize?: number;
    checksum?: string | null;
    metadata_payload?: Record<string, unknown> | null;
    metadataPayload?: Record<string, unknown> | null;
    created_at?: string;
    createdAt?: string;
  }[];
  code_edits?: {
    id: number;
    task_id?: number | null;
    review_chain_id?: number | null;
    actor_user_id?: number | null;
    actor_email?: string | null;
    chain_step_no?: number | null;
    review_chain_status?: string | null;
    workflow_stage?: string | null;
    review_round?: number | null;
    review_approved?: boolean | null;
    status: string;
    summary?: string | null;
    instructions: string;
    requested_files?: string[];
    changed_files?: string[];
    operations_count: number;
    diff_preview?: string | null;
    test_commands?: string[];
    test_results?: { command: string; returncode: number; stdout: string; stderr: string }[];
    model_mode?: string | null;
    raw_model_note?: string | null;
    rollback_status: string;
    rollback_error?: string | null;
    rollback_actor_user_id?: number | null;
    rollback_actor_email?: string | null;
    rolled_back_at?: string | null;
    created_at: string;
    updated_at: string;
    files?: { id: number; path: string; created_at: string }[];
  }[];
  code_edit_chains?: {
    id: number;
    task_id: number;
    status: string;
    started_review_round: number;
    current_review_round: number;
    total_executions: number;
    latest_review_summary?: string | null;
    latest_fix_instructions?: string | null;
    final_review_approved?: boolean | null;
    final_review_summary?: string | null;
    opened_at: string;
    closed_at?: string | null;
    created_at: string;
    updated_at: string;
  }[];
};

function getToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function saveToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function safeRequest<T>(path: string, fallback: T): Promise<T> {
  try {
    return await request<T>(path, { method: "GET" });
  } catch {
    return fallback;
  }
}

function normalizeTask(task: TaskItem | (TaskItem & Record<string, unknown>)): TaskItem {
  return {
    ...task,
    projectId: task.projectId ?? (task as unknown as { project_id?: number }).project_id ?? 1,
    userId: task.userId ?? (task as unknown as { user_id?: number }).user_id ?? 1,
    taskType: task.taskType ?? (task as unknown as { task_type?: string }).task_type ?? "text_to_video",
    templateId: task.templateId ?? (task as unknown as { template_id?: string }).template_id ?? "wanx-v1",
    workflowStage: task.workflowStage ?? (task as unknown as { workflow_stage?: string }).workflow_stage ?? "planning",
    planningStatus: task.planningStatus ?? (task as unknown as { planning_status?: string }).planning_status ?? "pending",
    executionStatus: task.executionStatus ?? (task as unknown as { execution_status?: string }).execution_status ?? "pending",
    reviewStatus: task.reviewStatus ?? (task as unknown as { review_status?: string }).review_status ?? "pending",
    executionMode: task.executionMode ?? (task as unknown as { execution_mode?: string }).execution_mode ?? "hybrid",
    quotedPrice: Number(task.quotedPrice ?? (task as unknown as { quoted_price?: number }).quoted_price ?? 0),
    finalCost: Number(task.finalCost ?? (task as unknown as { final_cost?: number }).final_cost ?? 0),
    finalCharge: Number(task.finalCharge ?? (task as unknown as { final_charge?: number }).final_charge ?? 0),
    selectedProvider: task.selectedProvider ?? (task as unknown as { selected_provider?: string }).selected_provider ?? null,
    selectedGpuType: task.selectedGpuType ?? (task as unknown as { selected_gpu_type?: string }).selected_gpu_type ?? null,
    retryLimit: task.retryLimit ?? (task as unknown as { retry_limit?: number }).retry_limit ?? 2,
    retryCount: task.retryCount ?? (task as unknown as { retry_count?: number }).retry_count ?? 0,
    lastError: task.lastError ?? (task as unknown as { last_error?: string }).last_error ?? null,
    planSummary: task.planSummary ?? (task as unknown as { plan_summary?: string }).plan_summary ?? null,
    executionBrief:
      task.executionBrief ?? (task as unknown as { execution_brief?: string }).execution_brief ?? null,
    codingInstructions:
      task.codingInstructions ??
      (task as unknown as { coding_instructions?: string }).coding_instructions ??
      null,
    reviewSummary: task.reviewSummary ?? (task as unknown as { review_summary?: string }).review_summary ?? null,
    latestFixInstructions:
      task.latestFixInstructions ??
      (task as unknown as { latest_fix_instructions?: string }).latest_fix_instructions ??
      null,
    resultSummary: task.resultSummary ?? (task as unknown as { result_summary?: string }).result_summary ?? null,
    reviewRound: task.reviewRound ?? (task as unknown as { review_round?: number }).review_round ?? 0,
    reviewApproved:
      task.reviewApproved ?? (task as unknown as { review_approved?: boolean }).review_approved ?? null,
    createdAt: task.createdAt ?? (task as unknown as { created_at?: string }).created_at ?? new Date().toISOString(),
    updatedAt: task.updatedAt ?? (task as unknown as { updated_at?: string }).updated_at ?? new Date().toISOString(),
  };
}

export async function login(email: string, password: string) {
  return request<AuthResult>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function register(email: string, phone: string, password: string) {
  return request<AuthResult>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, phone, password }),
  });
}

export async function fetchTasks() {
  const tasks = await safeRequest<TaskItem[]>("/api/tasks", MOCK_TASKS);
  return tasks.map((task) => normalizeTask(task));
}

export async function fetchAdminTasks() {
  const data = await request<{
    items?: TaskItem[];
    summary?: { total: number; running: number; failed: number; completed: number };
  }>("/api/admin/tasks", { method: "GET" });

  return {
    items: (data.items ?? []).map((task) => normalizeTask(task)),
    summary: data.summary ?? { total: 0, running: 0, failed: 0, completed: 0 },
  } satisfies AdminTaskBundle;
}

export async function fetchAdminTaskDetail(taskId: string) {
  const detail = await request<TaskDetail>(`/api/admin/tasks/${taskId}`, { method: "GET" });
  return {
    ...detail,
    task: normalizeTask(detail.task as TaskItem),
    current_run: detail.current_run,
    runs: detail.runs.map((run) => ({
        ...run,
        attemptNo: run.attemptNo ?? (run as unknown as { attempt_no?: number }).attempt_no ?? 1,
        gpuType: run.gpuType ?? (run as unknown as { gpu_type?: string }).gpu_type ?? "RTX 4090",
        runtimeTarget:
          run.runtimeTarget ?? (run as unknown as { runtime_target?: string }).runtime_target ?? "hybrid",
        providerCost:
          Number(run.providerCost ?? (run as unknown as { provider_cost?: number }).provider_cost ?? 0),
        schedulerScore:
          Number(run.schedulerScore ?? (run as unknown as { scheduler_score?: number }).scheduler_score ?? 0),
        failReason: run.failReason ?? (run as unknown as { fail_reason?: string }).fail_reason ?? null,
        localExecutorNote:
          run.localExecutorNote ??
          (run as unknown as { local_executor_note?: string }).local_executor_note ??
          null,
        startedAt: run.startedAt ?? (run as unknown as { started_at?: string }).started_at ?? null,
        endedAt: run.endedAt ?? (run as unknown as { ended_at?: string }).ended_at ?? null,
        createdAt: run.createdAt ?? (run as unknown as { created_at?: string }).created_at ?? new Date().toISOString(),
      })),
      events: detail.events.map((event) => ({
        ...event,
        detailPayload:
          event.detailPayload ??
          (event as unknown as { detail_payload?: Record<string, unknown> }).detail_payload ??
          null,
        createdAt:
          event.createdAt ??
          (event as unknown as { created_at?: string }).created_at ??
          new Date().toISOString(),
      })),
      artifacts: detail.artifacts.map((artifact) => ({
        ...artifact,
        storagePath: artifact.storagePath ?? artifact.storage_path ?? "/artifacts/placeholder.mp4",
        downloadUrl: artifact.downloadUrl ?? artifact.download_url ?? null,
        fileSize: artifact.fileSize ?? artifact.file_size ?? 0,
        checksum: artifact.checksum ?? null,
        metadataPayload: artifact.metadataPayload ?? artifact.metadata_payload ?? null,
        createdAt: artifact.createdAt ?? artifact.created_at ?? new Date().toISOString(),
      })),
      codeEdits:
        detail.code_edits?.map((item) => ({
          id: item.id,
          taskId: item.task_id ?? null,
          reviewChainId: item.review_chain_id ?? null,
          actorUserId: item.actor_user_id ?? null,
          actorEmail: item.actor_email ?? null,
          chainStepNo: item.chain_step_no ?? null,
          reviewChainStatus: item.review_chain_status ?? null,
          workflowStage: item.workflow_stage ?? null,
          reviewRound: item.review_round ?? null,
          reviewApproved: item.review_approved ?? null,
          status: item.status,
          summary: item.summary ?? null,
          instructions: item.instructions,
          requestedFiles: item.requested_files ?? [],
          changedFiles: item.changed_files ?? [],
          operationsCount: item.operations_count,
          diffPreview: item.diff_preview ?? null,
          testCommands: item.test_commands ?? [],
          testResults: item.test_results ?? [],
          modelMode: item.model_mode ?? null,
          rawModelNote: item.raw_model_note ?? null,
          rollbackStatus: item.rollback_status,
          rollbackError: item.rollback_error ?? null,
          rollbackActorUserId: item.rollback_actor_user_id ?? null,
          rollbackActorEmail: item.rollback_actor_email ?? null,
          rolledBackAt: item.rolled_back_at ?? null,
          createdAt: item.created_at,
          updatedAt: item.updated_at,
          files:
            item.files?.map((file) => ({
              id: file.id,
              path: file.path,
              createdAt: file.created_at,
            })) ?? [],
        })) ?? [],
    codeEditChains:
      detail.code_edit_chains?.map(
        (chain): CodeEditReviewChainItem => ({
            id: chain.id,
            taskId: chain.task_id,
            status: chain.status,
            startedReviewRound: chain.started_review_round,
            currentReviewRound: chain.current_review_round,
            totalExecutions: chain.total_executions,
            latestReviewSummary: chain.latest_review_summary ?? null,
            latestFixInstructions: chain.latest_fix_instructions ?? null,
            finalReviewApproved: chain.final_review_approved ?? null,
            finalReviewSummary: chain.final_review_summary ?? null,
            openedAt: chain.opened_at,
            closedAt: chain.closed_at ?? null,
            createdAt: chain.created_at,
            updatedAt: chain.updated_at,
        }),
      ) ?? [],
  };
}

export async function retryAdminTask(taskId: string) {
  return request<TaskItem>(`/api/admin/tasks/${taskId}/retry`, { method: "POST", body: JSON.stringify({}) });
}

export async function cancelAdminTask(taskId: string) {
  return request<TaskItem>(`/api/admin/tasks/${taskId}/cancel`, { method: "POST", body: JSON.stringify({}) });
}

export async function fetchAdminUsers() {
  const rows = await request<
    {
      id: number;
      email: string;
      role: string;
      status: string;
      wallet_balance?: number;
      frozen_balance?: number;
      total_tasks?: number;
      running_tasks?: number;
      completed_tasks?: number;
      failed_tasks?: number;
      created_at?: string;
    }[]
  >("/api/admin/users", { method: "GET" });
  return rows.map(
    (item): AdminUserOverview => ({
      id: item.id,
      email: item.email,
      role: item.role,
      status: item.status,
      walletBalance: Number((item as { walletBalance?: number }).walletBalance ?? item.wallet_balance ?? 0),
      frozenBalance: Number((item as { frozenBalance?: number }).frozenBalance ?? item.frozen_balance ?? 0),
      totalTasks: Number((item as { totalTasks?: number }).totalTasks ?? item.total_tasks ?? 0),
      runningTasks: Number((item as { runningTasks?: number }).runningTasks ?? item.running_tasks ?? 0),
      completedTasks: Number((item as { completedTasks?: number }).completedTasks ?? item.completed_tasks ?? 0),
      failedTasks: Number((item as { failedTasks?: number }).failedTasks ?? item.failed_tasks ?? 0),
      createdAt:
        (item as { createdAt?: string }).createdAt ??
        item.created_at ??
        new Date().toISOString(),
    }),
  );
}

export async function fetchTaskDetail(taskId: string) {
  try {
    const detail = await request<TaskDetail>(`/api/tasks/${taskId}`, { method: "GET" });
    return {
      ...detail,
      task: {
        ...(detail.task as unknown as TaskItem),
        projectId:
          (detail.task as unknown as { project_id?: number }).project_id ??
          (detail.task as unknown as TaskItem).projectId ??
          1,
        userId:
          (detail.task as unknown as { user_id?: number }).user_id ??
          (detail.task as unknown as TaskItem).userId ??
          1,
        taskType:
          (detail.task as unknown as { task_type?: string }).task_type ??
          (detail.task as unknown as TaskItem).taskType ??
          "text_to_video",
        templateId:
          (detail.task as unknown as { template_id?: string }).template_id ??
          (detail.task as unknown as TaskItem).templateId ??
          "wanx-v1",
        workflowStage:
          (detail.task as unknown as { workflow_stage?: string }).workflow_stage ??
          (detail.task as unknown as TaskItem).workflowStage ??
          "planning",
        planningStatus:
          (detail.task as unknown as { planning_status?: string }).planning_status ??
          (detail.task as unknown as TaskItem).planningStatus ??
          "pending",
        executionStatus:
          (detail.task as unknown as { execution_status?: string }).execution_status ??
          (detail.task as unknown as TaskItem).executionStatus ??
          "pending",
        reviewStatus:
          (detail.task as unknown as { review_status?: string }).review_status ??
          (detail.task as unknown as TaskItem).reviewStatus ??
          "pending",
        executionMode:
          (detail.task as unknown as { execution_mode?: string }).execution_mode ??
          (detail.task as unknown as TaskItem).executionMode ??
          "hybrid",
        selectedProvider:
          (detail.task as unknown as { selected_provider?: string }).selected_provider ??
          (detail.task as unknown as TaskItem).selectedProvider ??
          null,
        selectedGpuType:
          (detail.task as unknown as { selected_gpu_type?: string }).selected_gpu_type ??
          (detail.task as unknown as TaskItem).selectedGpuType ??
          null,
        retryLimit:
          (detail.task as unknown as { retry_limit?: number }).retry_limit ??
          (detail.task as unknown as TaskItem).retryLimit ??
          2,
        retryCount:
          (detail.task as unknown as { retry_count?: number }).retry_count ??
          (detail.task as unknown as TaskItem).retryCount ??
          0,
        planSummary:
          (detail.task as unknown as { plan_summary?: string }).plan_summary ??
          (detail.task as unknown as TaskItem).planSummary ??
          null,
        executionBrief:
          (detail.task as unknown as { execution_brief?: string }).execution_brief ??
          (detail.task as unknown as TaskItem).executionBrief ??
          null,
        codingInstructions:
          (detail.task as unknown as { coding_instructions?: string }).coding_instructions ??
          (detail.task as unknown as TaskItem).codingInstructions ??
          null,
        reviewSummary:
          (detail.task as unknown as { review_summary?: string }).review_summary ??
          (detail.task as unknown as TaskItem).reviewSummary ??
          null,
        latestFixInstructions:
          (detail.task as unknown as { latest_fix_instructions?: string }).latest_fix_instructions ??
          (detail.task as unknown as TaskItem).latestFixInstructions ??
          null,
        resultSummary:
          (detail.task as unknown as { result_summary?: string }).result_summary ??
          (detail.task as unknown as TaskItem).resultSummary ??
          null,
        reviewRound:
          (detail.task as unknown as { review_round?: number }).review_round ??
          (detail.task as unknown as TaskItem).reviewRound ??
          0,
        reviewApproved:
          (detail.task as unknown as { review_approved?: boolean }).review_approved ??
          (detail.task as unknown as TaskItem).reviewApproved ??
          null,
        lastError:
          (detail.task as unknown as { last_error?: string }).last_error ??
          (detail.task as unknown as TaskItem).lastError ??
          null,
        createdAt:
          (detail.task as unknown as { created_at?: string }).created_at ??
          (detail.task as unknown as TaskItem).createdAt ??
          new Date().toISOString(),
        updatedAt:
          (detail.task as unknown as { updated_at?: string }).updated_at ??
          (detail.task as unknown as TaskItem).updatedAt ??
          new Date().toISOString(),
      },
      current_run: detail.current_run,
      runs: detail.runs.map((run) => ({
        ...run,
        attemptNo: run.attemptNo ?? (run as unknown as { attempt_no?: number }).attempt_no ?? 1,
        gpuType: run.gpuType ?? (run as unknown as { gpu_type?: string }).gpu_type ?? "RTX 4090",
        runtimeTarget:
          run.runtimeTarget ?? (run as unknown as { runtime_target?: string }).runtime_target ?? "hybrid",
        providerCost:
          Number(run.providerCost ?? (run as unknown as { provider_cost?: number }).provider_cost ?? 0),
        schedulerScore:
          Number(run.schedulerScore ?? (run as unknown as { scheduler_score?: number }).scheduler_score ?? 0),
        failReason: run.failReason ?? (run as unknown as { fail_reason?: string }).fail_reason ?? null,
        localExecutorNote:
          run.localExecutorNote ??
          (run as unknown as { local_executor_note?: string }).local_executor_note ??
          null,
        startedAt: run.startedAt ?? (run as unknown as { started_at?: string }).started_at ?? null,
        endedAt: run.endedAt ?? (run as unknown as { ended_at?: string }).ended_at ?? null,
        createdAt: run.createdAt ?? (run as unknown as { created_at?: string }).created_at ?? new Date().toISOString(),
      })),
      events: detail.events.map((event) => ({
        ...event,
        detailPayload:
          event.detailPayload ??
          (event as unknown as { detail_payload?: Record<string, unknown> }).detail_payload ??
          null,
        createdAt:
          event.createdAt ??
          (event as unknown as { created_at?: string }).created_at ??
          new Date().toISOString(),
      })),
      artifacts: detail.artifacts.map((artifact) => ({
        ...artifact,
        storagePath: artifact.storagePath ?? artifact.storage_path ?? "/artifacts/placeholder.mp4",
        downloadUrl: artifact.downloadUrl ?? artifact.download_url ?? null,
        fileSize: artifact.fileSize ?? artifact.file_size ?? 0,
        checksum: artifact.checksum ?? null,
        metadataPayload: artifact.metadataPayload ?? artifact.metadata_payload ?? null,
        createdAt: artifact.createdAt ?? artifact.created_at ?? new Date().toISOString(),
      })),
      codeEdits:
        detail.code_edits?.map((item) => ({
          id: item.id,
          taskId: item.task_id ?? null,
          reviewChainId: item.review_chain_id ?? null,
          actorUserId: item.actor_user_id ?? null,
          actorEmail: item.actor_email ?? null,
          chainStepNo: item.chain_step_no ?? null,
          reviewChainStatus: item.review_chain_status ?? null,
          workflowStage: item.workflow_stage ?? null,
          reviewRound: item.review_round ?? null,
          reviewApproved: item.review_approved ?? null,
          status: item.status,
          summary: item.summary ?? null,
          instructions: item.instructions,
          requestedFiles: item.requested_files ?? [],
          changedFiles: item.changed_files ?? [],
          operationsCount: item.operations_count,
          diffPreview: item.diff_preview ?? null,
          testCommands: item.test_commands ?? [],
          testResults: item.test_results ?? [],
          modelMode: item.model_mode ?? null,
          rawModelNote: item.raw_model_note ?? null,
          rollbackStatus: item.rollback_status,
          rollbackError: item.rollback_error ?? null,
          rollbackActorUserId: item.rollback_actor_user_id ?? null,
          rollbackActorEmail: item.rollback_actor_email ?? null,
          rolledBackAt: item.rolled_back_at ?? null,
          createdAt: item.created_at,
          updatedAt: item.updated_at,
          files:
            item.files?.map((file) => ({
              id: file.id,
              path: file.path,
              createdAt: file.created_at,
            })) ?? [],
        })) ?? [],
      codeEditChains:
        detail.code_edit_chains?.map(
          (chain): CodeEditReviewChainItem => ({
            id: chain.id,
            taskId: chain.task_id,
            status: chain.status,
            startedReviewRound: chain.started_review_round,
            currentReviewRound: chain.current_review_round,
            totalExecutions: chain.total_executions,
            latestReviewSummary: chain.latest_review_summary ?? null,
            latestFixInstructions: chain.latest_fix_instructions ?? null,
            finalReviewApproved: chain.final_review_approved ?? null,
            finalReviewSummary: chain.final_review_summary ?? null,
            openedAt: chain.opened_at,
            closedAt: chain.closed_at ?? null,
            createdAt: chain.created_at,
            updatedAt: chain.updated_at,
          }),
        ) ?? [],
    };
  } catch {
    return MOCK_TASK_DETAIL;
  }
}

export async function fetchWallet() {
  try {
    const wallet = await request<WalletData & { frozen_balance?: number }>("/api/wallet", {
      method: "GET",
    });
    const ledger = await request<(WalletLedgerItem & { balance_after?: number; ref_type?: string; ref_id?: string; created_at?: string })[]>(
      "/api/wallet/ledger",
      { method: "GET" },
    );
    return {
      wallet: {
        ...wallet,
        frozenBalance: wallet.frozenBalance ?? wallet.frozen_balance ?? 0,
        createdAt: wallet.createdAt ?? (wallet as WalletData & { created_at?: string }).created_at ?? new Date().toISOString(),
      },
      ledger: ledger.map((item) => ({
        ...item,
        balanceAfter: item.balanceAfter ?? item.balance_after ?? 0,
        refType: item.refType ?? item.ref_type ?? null,
        refId: item.refId ?? item.ref_id ?? null,
        createdAt: item.createdAt ?? item.created_at ?? new Date().toISOString(),
      })),
    };
  } catch {
    return { wallet: MOCK_WALLET, ledger: MOCK_LEDGER };
  }
}

export async function rechargeWallet(amount: number) {
  return request("/api/wallet/recharge", {
    method: "POST",
    body: JSON.stringify({ amount, method: "manual" }),
  });
}

export async function fetchOffers() {
  const offers = await safeRequest<(ProviderOffer & { gpu_type?: string; price_per_hour?: number; reliability_score?: number; startup_score?: number; success_rate?: number })[]>(
    "/api/providers/offers",
    MOCK_OFFERS,
  );
  return offers.map((offer) => ({
    ...offer,
    gpuType: offer.gpuType ?? offer.gpu_type ?? "RTX 4090",
    pricePerHour: offer.pricePerHour ?? offer.price_per_hour ?? 0,
    reliabilityScore: offer.reliabilityScore ?? offer.reliability_score ?? 0,
    startupScore: offer.startupScore ?? offer.startup_score ?? 0,
    successRate: offer.successRate ?? offer.success_rate ?? 0,
  }));
}

export async function fetchQuote(payload: {
  task_type: string;
  strategy: string;
  duration_seconds: number;
  resolution: string;
  output_count: number;
  execution_mode: string;
}) {
  try {
    return await request<{
      recommended_offer: ProviderOffer;
      candidate_offers: ProviderOffer[];
      estimated_price: number;
      estimated_runtime_minutes: number;
      risk_note: string;
    }>("/api/quotes", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  } catch {
    return {
      recommended_offer: MOCK_OFFERS[1],
      candidate_offers: MOCK_OFFERS,
      estimated_price: 18.6,
      estimated_runtime_minutes: 12,
      risk_note: "当前为 mock 报价结果。",
    };
  }
}

export async function createTask(payload: Record<string, unknown>) {
  return request<TaskItem>("/api/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function retryTask(taskId: string) {
  return request<TaskItem>(`/api/tasks/${taskId}/retry`, { method: "POST", body: JSON.stringify({}) });
}

export async function cancelTask(taskId: string) {
  return request<TaskItem>(`/api/tasks/${taskId}/cancel`, { method: "POST", body: JSON.stringify({}) });
}

export async function requestArtifactDownload(taskId: number, artifactId: number) {
  return request<{ artifact_id: number; download_url: string; source: string }>(
    `/api/tasks/${taskId}/artifacts/${artifactId}/download`,
    { method: "GET" },
  );
}

export async function fetchProviderHealth() {
  const rows = await safeRequest<(ProviderHealth & { offer_count?: number; average_price_per_hour?: number; average_reliability?: number; average_startup_score?: number; average_success_rate?: number })[]>(
    "/api/admin/providers/health",
    MOCK_PROVIDER_HEALTH,
  );
  return rows.map((row) => ({
    ...row,
    offerCount: row.offerCount ?? row.offer_count ?? 0,
    averagePricePerHour: row.averagePricePerHour ?? row.average_price_per_hour ?? 0,
    averageReliability: row.averageReliability ?? row.average_reliability ?? 0,
    averageStartupScore: row.averageStartupScore ?? row.average_startup_score ?? 0,
    averageSuccessRate: row.averageSuccessRate ?? row.average_success_rate ?? 0,
  }));
}

export async function fetchBilling() {
  const billing = await safeRequest<BillingSnapshot & { gross_profit?: number; gross_margin?: number; by_provider?: { provider: string; cost: number; run_count?: number }[] }>(
    "/api/admin/billing/profit",
    MOCK_BILLING,
  );
  return {
    ...billing,
    grossProfit: billing.grossProfit ?? billing.gross_profit ?? 0,
    grossMargin: billing.grossMargin ?? billing.gross_margin ?? 0,
    byProvider:
      billing.byProvider ??
      billing.by_provider?.map((item) => ({
        provider: item.provider,
        cost: item.cost,
        runCount: item.run_count ?? 0,
      })) ??
      [],
  };
}

export async function fetchExecutionHealth() {
  return safeRequest<{ mode: string; status: string }>("/api/admin/execution/health", {
    mode: "simulated",
    status: "unknown",
  });
}

export async function fetchMonitoringOverview() {
  const data = await safeRequest<
    {
      status_breakdown?: Record<string, number>;
      active_runs?: number;
      queued_for_retry?: number;
      pending_cleanup?: number;
      open_cancellations?: number;
      recent_provider_cost?: number;
      recent_runtime_seconds?: number;
      adapter_key?: string;
      marketplace_name?: string;
      recent_failures?: {
        task_id: number;
        status: string;
        provider?: string | null;
        retry_count: number;
        last_error?: string | null;
        updated_at?: string | null;
      }[];
    }
  >("/api/admin/monitoring/overview", {});

  const fallback: MonitoringOverview = {
    statusBreakdown: {},
    activeRuns: 0,
    queuedForRetry: 0,
    pendingCleanup: 0,
    openCancellations: 0,
    recentProviderCost: 0,
    recentRuntimeSeconds: 0,
    adapterKey: "unknown",
    marketplaceName: "unknown",
    recentFailures: [],
  };
  if (!Object.keys(data).length) {
    return fallback;
  }

  return {
    statusBreakdown: data.status_breakdown ?? {},
    activeRuns: data.active_runs ?? 0,
    queuedForRetry: data.queued_for_retry ?? 0,
    pendingCleanup: data.pending_cleanup ?? 0,
    openCancellations: data.open_cancellations ?? 0,
    recentProviderCost: data.recent_provider_cost ?? 0,
    recentRuntimeSeconds: data.recent_runtime_seconds ?? 0,
    adapterKey: data.adapter_key ?? "unknown",
    marketplaceName: data.marketplace_name ?? "unknown",
    recentFailures:
      data.recent_failures?.map((item) => ({
        taskId: item.task_id,
        status: item.status,
        provider: item.provider ?? null,
        retryCount: item.retry_count,
        lastError: item.last_error ?? null,
        updatedAt: item.updated_at ?? null,
      })) ?? [],
  };
}

export async function fetchHomeMetrics() {
  const data = await safeRequest<{
    average_delivery_seconds?: number;
    success_rate_7d?: number;
    provider_count?: number;
    cost_visibility_coverage?: number;
    sample_size_7d?: number;
    completed_tasks_7d?: number;
    updated_at?: string;
  }>("/api/home/metrics", {});

  if (!Object.keys(data).length) {
    return {
      averageDeliverySeconds: 0,
      successRate7d: 0,
      providerCount: 0,
      costVisibilityCoverage: 0,
      sampleSize7d: 0,
      completedTasks7d: 0,
      updatedAt: new Date().toISOString(),
    } satisfies HomeMetrics;
  }

  return {
    averageDeliverySeconds: data.average_delivery_seconds ?? 0,
    successRate7d: data.success_rate_7d ?? 0,
    providerCount: data.provider_count ?? 0,
    costVisibilityCoverage: data.cost_visibility_coverage ?? 0,
    sampleSize7d: data.sample_size_7d ?? 0,
    completedTasks7d: data.completed_tasks_7d ?? 0,
    updatedAt: data.updated_at ?? new Date().toISOString(),
  } satisfies HomeMetrics;
}

export async function runExecutionOnce() {
  return request<{ processed_count: number; items: { task_id: number; status: string; retry_count?: number }[] }>(
    "/api/admin/execution/run-once",
    {
      method: "POST",
      body: JSON.stringify({}),
    },
  );
}

export async function runCodeEdit(payload: {
  instructions: string;
  files: string[];
  test_commands?: string[];
  task_id?: number | null;
}) {
  return request<{
    summary: string;
    mode: string;
    changed_files: string[];
    operations_count: number;
    execution_id?: number | null;
    task_id?: number | null;
    review_chain_id?: number | null;
    chain_step_no?: number | null;
    review_chain_status?: string | null;
    workflow_stage?: string | null;
    review_round?: number | null;
    review_approved?: boolean | null;
    diff_preview?: string | null;
    test_results?: { command: string; returncode: number; stdout: string; stderr: string }[];
    raw_model_note?: string | null;
    rollback_status?: string | null;
  }>("/api/admin/execution/code-edit", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function previewCodeEdit(payload: { instructions: string; files: string[] }) {
  return request<{
    summary: string;
    mode: string;
    changed_files: string[];
    operations_count: number;
    diff_preview?: string | null;
    test_results?: { command: string; returncode: number; stdout: string; stderr: string }[];
    raw_model_note?: string | null;
  }>("/api/admin/execution/code-edit/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchCodeEditHistory(taskId?: number) {
  const rows = await safeRequest<
    {
      id: number;
      actor_user_id?: number | null;
      actor_email?: string | null;
      status: string;
      summary?: string | null;
      instructions: string;
      requested_files?: string[];
      changed_files?: string[];
      operations_count: number;
      diff_preview?: string | null;
      test_commands?: string[];
      test_results?: { command: string; returncode: number; stdout: string; stderr: string }[];
      model_mode?: string | null;
      raw_model_note?: string | null;
      rollback_status: string;
      rollback_error?: string | null;
      rollback_actor_user_id?: number | null;
      rollback_actor_email?: string | null;
      rolled_back_at?: string | null;
      created_at: string;
      updated_at: string;
      files?: { id: number; path: string; created_at: string }[];
    }[]
  >(`/api/admin/execution/code-edits${taskId ? `?task_id=${taskId}` : ""}`, []);
  return rows.map(
    (row): CodeEditHistoryItem => ({
      id: row.id,
      taskId: (row as { task_id?: number | null }).task_id ?? null,
      reviewChainId:
        (row as { review_chain_id?: number | null }).review_chain_id ?? null,
      actorUserId: row.actor_user_id ?? null,
      actorEmail: row.actor_email ?? null,
      chainStepNo: (row as { chain_step_no?: number | null }).chain_step_no ?? null,
      reviewChainStatus:
        (row as { review_chain_status?: string | null }).review_chain_status ?? null,
      workflowStage: (row as { workflow_stage?: string | null }).workflow_stage ?? null,
      reviewRound: (row as { review_round?: number | null }).review_round ?? null,
      reviewApproved: (row as { review_approved?: boolean | null }).review_approved ?? null,
      status: row.status,
      summary: row.summary ?? null,
      instructions: row.instructions,
      requestedFiles: row.requested_files ?? [],
      changedFiles: row.changed_files ?? [],
      operationsCount: row.operations_count,
      diffPreview: row.diff_preview ?? null,
      testCommands: row.test_commands ?? [],
      testResults: row.test_results ?? [],
      modelMode: row.model_mode ?? null,
      rawModelNote: row.raw_model_note ?? null,
      rollbackStatus: row.rollback_status,
      rollbackError: row.rollback_error ?? null,
      rollbackActorUserId: row.rollback_actor_user_id ?? null,
      rollbackActorEmail: row.rollback_actor_email ?? null,
      rolledBackAt: row.rolled_back_at ?? null,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
      files:
        row.files?.map((file) => ({
          id: file.id,
          path: file.path,
          createdAt: file.created_at,
        })) ?? [],
    }),
  );
}

export async function rollbackCodeEdit(executionId: number) {
  return request<{
    execution_id: number;
    rollback_status: string;
    restored_files: string[];
    message: string;
  }>(`/api/admin/execution/code-edit/${executionId}/rollback`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}
