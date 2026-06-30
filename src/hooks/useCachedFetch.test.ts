import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { useCachedFetch } from "./useCachedFetch";

describe("useCachedFetch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("retorna loading=true inicialmente e os dados após o fetch resolver", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ valor: 42 }),
    }) as any;

    const { result } = renderHook(() => useCachedFetch<{ valor: number }>("/api/teste"));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual({ valor: 42 });
    expect(result.current.error).toBeNull();
  });

  it("ignora resposta obsoleta quando a key muda antes do fetch anterior resolver", async () => {
    let resolveFirst: (v: any) => void;
    const firstPromise = new Promise((resolve) => { resolveFirst = resolve; });
    global.fetch = vi.fn()
      .mockImplementationOnce(() => firstPromise)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ valor: 2 }) }) as any;

    const { result, rerender } = renderHook(
      ({ key }) => useCachedFetch<{ valor: number }>(`/api/${key}`),
      { initialProps: { key: "a" } }
    );

    rerender({ key: "b" });
    await waitFor(() => expect(result.current.data).toEqual({ valor: 2 }));

    resolveFirst!({ ok: true, json: async () => ({ valor: 1 }) });
    await new Promise((r) => setTimeout(r, 10));

    expect(result.current.data).toEqual({ valor: 2 });
  });

  it("usa body.detail como mensagem de erro quando a resposta HTTP nao eh ok", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "Dados insuficientes" }),
    }) as any;

    const { result } = renderHook(() => useCachedFetch<{ valor: number }>("/api/erro"));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Dados insuficientes");
    expect(result.current.data).toBeNull();
  });
});
