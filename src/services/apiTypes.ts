export type ApiError = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

export type ApiResponse<T> = { data: T; error: null } | { data: null; error: ApiError };

export function ok<T>(data: T): ApiResponse<T> {
  return { data, error: null };
}

export function fail<T = never>(
  code: string,
  message: string,
  details?: Record<string, unknown>
): ApiResponse<T> {
  return {
    data: null,
    error: {
      code,
      message,
      details
    }
  };
}
