import { useCallback, useEffect, useRef, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { chatApi, type ChatTurn, type SkillSummary } from "@/api/chat";

interface UiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  meta?: ChatTurn;
}

export function ChatTab() {
  const [skills, setSkills] = useState<SkillSummary[] | null>(null);
  const [keyHealth, setKeyHealth] = useState<{ anthropic_key_set: boolean; model: string } | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    chatApi.skills().then((s) => setSkills(s.skills)).catch((e) => setError(String(e)));
    chatApi.health().then((h) =>
      setKeyHealth({ anthropic_key_set: h.anthropic_key_set, model: h.model }),
    ).catch(() => null);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useCallback(
    async (raw: string) => {
      const text = raw.trim();
      if (!text || sending) return;
      const userMsg: UiMessage = { id: `u${Date.now()}`, role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setSending(true);
      setError(null);
      try {
        const r = await chatApi.send(text, sessionId);
        if (!sessionId) setSessionId(r.session_id);
        const assistantMsg: UiMessage = {
          id: `a${Date.now()}`,
          role: "assistant",
          content: r.turn.content,
          meta: r.turn,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setSending(false);
      }
    },
    [sending, sessionId],
  );

  const insertSlash = useCallback((skill: string) => {
    setInput((prev) => (prev ? `/${skill} ${prev}` : `/${skill} `));
  }, []);

  const reset = useCallback(async () => {
    if (sessionId) {
      try {
        await chatApi.clear(sessionId);
      } catch {}
    }
    setMessages([]);
    setSessionId(null);
    setInput("");
    setError(null);
  }, [sessionId]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle>oh-my-tiny-oran (chat harness)</CardTitle>
            <CardDescription>
              Tiny OMC-shaped chat scoped to the oran-discover bundle. Slash commands inline the
              skill markdown into the next message, exactly the way upstream OMC's keyword-detector
              does. Read-only tools: curl the lab's HTTP wrappers, read committed repo files.
            </CardDescription>
          </div>
          {keyHealth && (
            <div className="text-xs text-right">
              <Badge variant={keyHealth.anthropic_key_set ? "success" : "danger"}>
                {keyHealth.anthropic_key_set ? "key set" : "no key"}
              </Badge>
              <div className="text-muted-foreground mt-1 font-mono">{keyHealth.model}</div>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-1 text-xs">
          <span className="text-muted-foreground self-center mr-1">slash shortcuts:</span>
          {skills?.map((s) => (
            <Button key={s.name} onClick={() => insertSlash(s.name)} className="text-xs">
              /{s.name.replace("oran-discover:", "")}
            </Button>
          ))}
          <Button onClick={reset} className="ml-auto text-xs">new session</Button>
        </div>

        <ScrollArea className="h-[55vh] rounded border bg-muted">
          <div className="p-3 space-y-3">
            {messages.length === 0 && (
              <div className="text-xs text-muted-foreground italic">
                Try: "what does the lab look like right now?" or "/oran-discover:plan", or pick a
                skill shortcut above to pre-fill the input.
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className={m.role === "user" ? "text-right" : "text-left"}>
                <div
                  className={
                    "inline-block max-w-full rounded px-3 py-2 text-xs whitespace-pre-wrap font-mono " +
                    (m.role === "user" ? "bg-primary text-primary-foreground" : "bg-background border")
                  }
                >
                  {m.content || "(no content)"}
                </div>
                {m.meta && (
                  <div className="text-[10px] text-muted-foreground mt-1 flex flex-wrap gap-1 justify-start">
                    <Badge variant="muted">{m.meta.latency_s}s</Badge>
                    <Badge variant="muted">in {m.meta.input_tokens}</Badge>
                    <Badge variant="muted">out {m.meta.output_tokens}</Badge>
                    {m.meta.skill_invoked && <Badge variant="default">{m.meta.skill_invoked}</Badge>}
                    {m.meta.tool_uses.length > 0 && (
                      <Badge variant="warning">{m.meta.tool_uses.length} tool calls</Badge>
                    )}
                  </div>
                )}
                {m.meta && m.meta.tool_uses.length > 0 && (
                  <ul className="text-[10px] font-mono text-muted-foreground mt-1 space-y-0.5 text-left">
                    {m.meta.tool_uses.map((tu, i) => (
                      <li key={i}>
                        <span className="text-primary">{tu.name}</span>({JSON.stringify(tu.input)})
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>

        {error && <div className="text-xs text-red-700">error: {error}</div>}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder='Type a question or "/oran-discover:plan"...'
            className="flex-1 rounded border px-2 py-1 text-xs font-mono bg-background"
            disabled={sending}
          />
          <Button type="submit" disabled={sending || !input.trim()} className="bg-primary text-primary-foreground">
            {sending ? "..." : "Send"}
          </Button>
        </form>
        {sessionId && (
          <div className="text-[10px] text-muted-foreground font-mono">session: {sessionId}</div>
        )}
      </CardContent>
    </Card>
  );
}
