import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../services/apiClient";
import { appToday } from "../services/dateContext";
import type { PlanContextValue, PlanCoverageStatus, UserProfile } from "../types/domain";

const PlanContext = createContext<PlanContextValue | null>(null);

export function PlanProvider({ children, userId }: { children: ReactNode; userId: string }) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [currentPlan, setCurrentPlan] = useState<PlanContextValue["currentPlan"]>(null);
  const [coverageStatus, setCoverageStatus] = useState<PlanCoverageStatus>("none");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshPlanState = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const [profileResponse, planResponse] = await Promise.all([
      api.getProfile(userId),
      api.getCurrentPlan(userId)
    ]);

    const errors = [profileResponse.error?.message, planResponse.error?.message].filter(
      (message): message is string => Boolean(message)
    );

    setProfile(profileResponse.error ? null : profileResponse.data);
    if (planResponse.error) {
      setCurrentPlan(null);
      setCoverageStatus("none");
    } else {
      setCurrentPlan(planResponse.data.plan);
      setCoverageStatus(planResponse.data.coverage_status);
    }

    setError(errors.length ? errors.join(" ") : null);
    setIsLoading(false);
  }, [userId]);

  useEffect(() => {
    void refreshPlanState();
  }, [refreshPlanState]);

  const value = useMemo(
    () => ({ profile, currentPlan, coverageStatus, refreshPlanState, today: appToday, isLoading, error }),
    [coverageStatus, currentPlan, error, isLoading, profile, refreshPlanState]
  );

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
}

export function usePlanContext() {
  const context = useContext(PlanContext);
  if (!context) throw new Error("usePlanContext must be used within a PlanProvider.");
  return context;
}
