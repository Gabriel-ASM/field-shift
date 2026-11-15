/** A run as a polled job: start it, report the trajectories done, resolve with the result and the job id. */

import { getJob, startJob, type RunOptions } from "./api.ts";
import type { JobView, RunResult } from "./types.ts";

export interface Progress {
  done: number;
  total: number;
}

export interface JobApi {
  start: (options: RunOptions) => Promise<{ id: string; total: number }>;
  poll: (id: string) => Promise<JobView>;
  wait: (milliseconds: number) => Promise<void>;
}

const POLL_EVERY = 400;

export const networkJobs: JobApi = {
  start: startJob,
  poll: getJob,
  wait: (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
};

export async function runJob(options: RunOptions, onProgress: (progress: Progress) => void, api: JobApi = networkJobs): Promise<{ job: string; result: RunResult }> {
  const { id, total } = await api.start(options);
  onProgress({ done: 0, total });
  for (;;) {
    const view = await api.poll(id);
    onProgress({ done: view.done, total: view.total });
    if (view.status === "done" && view.result) return { job: id, result: view.result };
    if (view.status === "failed") throw new Error(view.error ?? "the simulation failed");
    await api.wait(POLL_EVERY);
  }
}
