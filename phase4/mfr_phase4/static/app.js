(function () {
  const STORAGE_KEY = "mfr_thread_id";
  const API_BASE =
    typeof window !== "undefined" &&
    window.location &&
    window.location.protocol === "file:"
      ? "http://127.0.0.1:8000"
      : "";

  const fetchOpts = { cache: "no-store" };

  function apiUrl(path) {
    return API_BASE + path;
  }

  const form = document.getElementById("chat-form");
  const q = document.getElementById("q");
  const err = document.getElementById("err");
  const newThreadBtn = document.getElementById("new-thread");
  const clearOtherBtn = document.getElementById("clear-other-chats");
  const clearAllBtn = document.getElementById("clear-all-chats");
  const threadListEl = document.getElementById("thread-list");
  const transcript = document.getElementById("transcript");
  const transcriptWrap = document.getElementById("transcript-wrap");
  const sendBtn = document.getElementById("send");

  if (
    !form ||
    !q ||
    !sendBtn ||
    !transcript ||
    !transcriptWrap ||
    !threadListEl ||
    !clearOtherBtn ||
    !clearAllBtn
  ) {
    return;
  }

  function getThreadId() {
    return sessionStorage.getItem(STORAGE_KEY);
  }

  function setThreadId(id) {
    if (id) sessionStorage.setItem(STORAGE_KEY, id);
    else sessionStorage.removeItem(STORAGE_KEY);
    syncClearOtherState();
  }

  function syncClearOtherState() {
    clearOtherBtn.disabled = !getThreadId();
  }

  function showErr(msg) {
    err.textContent = msg;
    err.hidden = false;
  }

  function formatThreadTime(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso).slice(0, 16);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function renderTranscript(messages) {
    transcript.innerHTML = "";
    if (!messages || !messages.length) {
      transcriptWrap.hidden = true;
      return;
    }
    transcriptWrap.hidden = false;
    messages.forEach(function (m) {
      var div = document.createElement("div");
      var isUser = m.role === "user";
      div.className = "msg " + (isUser ? "msg-user" : "msg-assistant");
      var label = document.createElement("div");
      label.className = "msg-role";
      label.textContent = isUser ? "You" : "Assistant";
      div.appendChild(label);
      var body = document.createElement("div");
      body.textContent = m.content || "";
      div.appendChild(body);
      transcript.appendChild(div);
    });
    transcript.scrollTop = transcript.scrollHeight;
  }

  async function fetchMessages(threadId) {
    if (!threadId) return [];
    var res = await fetch(
      apiUrl("/v1/chat/threads/" + encodeURIComponent(threadId) + "/messages"),
      fetchOpts
    );
    if (!res.ok) return [];
    var data = await res.json().catch(function () {
      return { messages: [] };
    });
    return data.messages || [];
  }

  async function refreshThreadList(activeId) {
    var res = await fetch(apiUrl("/v1/chat/threads"), fetchOpts);
    if (!res.ok) {
      if (res.status === 404) {
        showErr(
          "Chat API not found. Start the server from the project folder: python -m mfr_phase4"
        );
      }
      return;
    }
    err.hidden = true;
    var data = await res.json().catch(function () {
      return { threads: [] };
    });
    var threads = data.threads || [];
    threadListEl.innerHTML = "";
    threads.forEach(function (t) {
      var li = document.createElement("li");
      var btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.threadId = t.thread_id;
      if (t.thread_id === activeId) btn.classList.add("is-active");
      var prev = document.createElement("span");
      prev.className = "thread-preview";
      prev.textContent = t.preview || "New chat";
      btn.appendChild(prev);
      var meta = document.createElement("span");
      meta.className = "thread-meta";
      meta.textContent = formatThreadTime(t.updated_at);
      btn.appendChild(meta);
      btn.addEventListener("click", function () {
        selectThread(t.thread_id).catch(function (e) {
          showErr(String(e.message || e));
        });
      });
      li.appendChild(btn);
      threadListEl.appendChild(li);
    });
    syncClearOtherState();
  }

  async function selectThread(threadId) {
    setThreadId(threadId);
    await refreshThreadList(threadId);
    var msgs = await fetchMessages(threadId);
    renderTranscript(msgs);
  }

  document.querySelectorAll("button.example").forEach(function (btn) {
    btn.addEventListener("click", function () {
      q.value = btn.getAttribute("data-q") || "";
      q.focus();
    });
  });

  newThreadBtn.addEventListener("click", async function () {
    err.hidden = true;
    try {
      var res = await fetch(apiUrl("/v1/chat/threads"), Object.assign({ method: "POST" }, fetchOpts));
      if (!res.ok) throw new Error("Could not start a new chat (HTTP " + res.status + ")");
      var data = await res.json().catch(function () {
        return {};
      });
      var id = data.thread_id;
      if (!id) throw new Error("Invalid response from server");
      setThreadId(id);
      q.value = "";
      renderTranscript([]);
      transcriptWrap.hidden = true;
      await refreshThreadList(id);
      q.focus();
    } catch (ex) {
      showErr(String(ex.message || ex));
    }
  });

  clearOtherBtn.addEventListener("click", async function () {
    var keep = getThreadId();
    if (!keep) return;
    if (!window.confirm("Remove all conversations except the current one?")) return;
    err.hidden = true;
    try {
      var res = await fetch(
        apiUrl("/v1/chat/threads?keep=" + encodeURIComponent(keep)),
        Object.assign({ method: "DELETE" }, fetchOpts)
      );
      if (!res.ok) throw new Error("Could not clear chats (HTTP " + res.status + ")");
      await refreshThreadList(keep);
      var msgs = await fetchMessages(keep);
      renderTranscript(msgs);
    } catch (ex) {
      showErr(String(ex.message || ex));
    }
  });

  clearAllBtn.addEventListener("click", async function () {
    if (!window.confirm("Remove every conversation from the server? This cannot be undone."))
      return;
    err.hidden = true;
    try {
      var res = await fetch(apiUrl("/v1/chat/threads"), Object.assign({ method: "DELETE" }, fetchOpts));
      if (!res.ok) throw new Error("Could not clear chats (HTTP " + res.status + ")");
      setThreadId(null);
      renderTranscript([]);
      transcriptWrap.hidden = true;
      q.value = "";
      await refreshThreadList("");
    } catch (ex) {
      showErr(String(ex.message || ex));
    }
  });

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    err.hidden = true;

    var query = q.value.trim();
    if (!query) return;

    var tid = getThreadId();
    if (!tid) {
      try {
        var cr = await fetch(apiUrl("/v1/chat/threads"), Object.assign({ method: "POST" }, fetchOpts));
        if (!cr.ok) throw new Error("Could not create thread (HTTP " + cr.status + ")");
        var cj = await cr.json().catch(function () {
          return {};
        });
        tid = cj.thread_id;
        if (!tid) throw new Error("No thread_id from server");
        setThreadId(tid);
      } catch (ex) {
        showErr(String(ex.message || ex));
        return;
      }
    }

    var sentThreadId = tid;
    sendBtn.disabled = true;
    try {
      var res = await fetch(apiUrl("/v1/chat/respond"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          thread_id: sentThreadId,
          query: query,
        }),
        cache: "no-store",
      });
      var data = await res.json().catch(function () {
        return {};
      });
      if (!res.ok) {
        var d = data.detail;
        var msg =
          typeof d === "string"
            ? d
            : Array.isArray(d)
            ? JSON.stringify(d)
            : res.statusText || "Request failed (" + res.status + ")";
        throw new Error(msg);
      }

      if (data.thread_id) {
        setThreadId(data.thread_id);
      }
      var activeTid = data.thread_id || sentThreadId;
      if (!activeTid) {
        throw new Error("Server did not return a thread id");
      }

      var msgs = await fetchMessages(activeTid);
      if (
        (!msgs || !msgs.length) &&
        (data.answer_text || data.formatted_message)
      ) {
        msgs = [
          { role: "user", content: query, created_at: "" },
          {
            role: "assistant",
            content: data.formatted_message || data.answer_text || "",
            created_at: "",
          },
        ];
      }
      renderTranscript(msgs);
      await refreshThreadList(activeTid);
    } catch (ex) {
      showErr(String(ex.message || ex));
    } finally {
      sendBtn.disabled = false;
    }
  });

  (async function init() {
    syncClearOtherState();
    try {
      var tid = getThreadId();
      if (tid) {
        var ok = await fetch(
          apiUrl("/v1/chat/threads/" + encodeURIComponent(tid) + "/messages"),
          fetchOpts
        );
        if (!ok.ok) {
          setThreadId(null);
          tid = null;
        }
      }
      if (tid) {
        await selectThread(tid);
      } else {
        await refreshThreadList("");
      }
    } catch (e) {
      showErr("Could not load chats: " + String(e.message || e));
    }
  })();
})();
