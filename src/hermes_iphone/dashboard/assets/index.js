(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) return;
  const React = SDK.React;
  const h = React.createElement;
  const hooks = SDK.hooks || React;
  const C = SDK.components || {};
  const Card = C.Card || "div";
  const CardHeader = C.CardHeader || "div";
  const CardTitle = C.CardTitle || "h2";
  const CardContent = C.CardContent || "div";
  const Badge = C.Badge || "span";
  const Button = C.Button || "button";
  const Input = C.Input || "input";
  const Label = C.Label || "label";
  const api = (path, options) => SDK.fetchJSON(`/api/plugins/hermes-iphone-plugin${path}`, options);

  const READ_GROUPS = [
    ["Status", [["status", "Plugin"], ["devices", "Devices"], ["screen", "Screen"], ["current-app", "Current app"], ["snapshot", "Snapshot"]]],
    ["Debug", [["describe", "Describe"], ["tree", "Tree"], ["last-trace", "Last trace"], ["action-logs", "Action logs"]]],
  ];

  const ACTION_GROUPS = [
    ["Readiness & artifacts", [["ensure-wda", "Ensure WDA"], ["screenshot", "Screenshot"]]],
    ["Navigation", [["home", "Home"], ["go-back", "Back/Cancel"], ["dismiss-keyboard", "Dismiss keyboard"], ["recover-home", "Recover home"]]],
    ["Apps", [["launch-messages", "Messages"], ["launch-safari", "Safari"], ["launch-app", "Launch bundle"], ["open-url", "Open URL"]]],
    ["Device", [["lock", "Lock phone"]]],
  ];

  function JsonBlock({ data }) {
    const displayData = data && data.display_payload ? data.display_payload : data;
    return h("pre", { className: "iphone-json" }, JSON.stringify(displayData, null, 2));
  }

  function Field({ label, children }) {
    return h("div", { className: "iphone-field" }, h(Label, null, label), children);
  }

  function TextInput({ label, value, setValue, placeholder }) {
    return h(Field, { label }, h(Input, {
      value: value || "",
      placeholder,
      onChange: (event) => setValue(event.target.value),
    }));
  }

  function section(overview, key) {
    return (overview && overview.sections && overview.sections[key]) || {};
  }

  function payloadData(payload) {
    return (payload && payload.data) || {};
  }

  function okLabel(value) {
    return value ? "ok" : "issue";
  }

  function StatusPill({ label, value }) {
    return h("div", { className: "iphone-pill-row" },
      h("span", null, label),
      h(Badge, { className: value ? "iphone-ok" : "iphone-warn" }, okLabel(value))
    );
  }

  function OverviewCards({ overview }) {
    const status = section(overview, "status");
    const devices = section(overview, "devices");
    const screen = section(overview, "screen");
    const current = section(overview, "current_app");
    const snapshot = section(overview, "snapshot");
    const deviceList = payloadData(devices).devices || [];
    const screenData = payloadData(screen);
    const appData = payloadData(current);
    const snapshotData = payloadData(snapshot);
    const currentTree = snapshotData.tree || {};
    return h("div", { className: "iphone-overview-grid" },
      h(Card, { className: "iphone-card-accent" },
        h(CardHeader, null, h(CardTitle, null, "Readiness")),
        h(CardContent, null,
          h(StatusPill, { label: "Plugin", value: Boolean(status && status.ok) }),
          h(StatusPill, { label: "Device visible", value: deviceList.length > 0 }),
          h(StatusPill, { label: "WDA reads", value: Boolean(screen && screen.ok) }),
          h("p", { className: "iphone-muted" }, `Backend: ${(payloadData(status).backend || status.backend || "unknown")}`)
        )
      ),
      h(Card, null,
        h(CardHeader, null, h(CardTitle, null, "Device")),
        h(CardContent, null,
          h("div", { className: "iphone-big-number" }, String(deviceList.length)),
          h("p", { className: "iphone-muted" }, deviceList.length === 1 ? "attached device" : "attached devices"),
          deviceList.slice(0, 2).map((device, index) => h("small", { key: index, className: "iphone-line" }, device.name || device.udid || device.identifier || "iPhone"))
        )
      ),
      h(Card, null,
        h(CardHeader, null, h(CardTitle, null, "Current app")),
        h(CardContent, null,
          h("strong", null, appData.name || currentTree.name || "Unknown"),
          h("p", { className: "iphone-muted" }, appData.bundle_id || currentTree.bundle_id || "No bundle id yet"),
          h("small", { className: "iphone-line" }, screenData.width && screenData.height ? `${screenData.width} × ${screenData.height}` : "screen size unavailable")
        )
      ),
      h(Card, null,
        h(CardHeader, null, h(CardTitle, null, "Screen summary")),
        h(CardContent, null,
          h("p", { className: "iphone-summary" }, snapshotData.summary || payloadData(section(overview, "current_app")).summary || "Run Snapshot or Describe for visible UI details."),
          h("small", { className: "iphone-line" }, currentTree.elements ? `${currentTree.elements.length} semantic elements sampled` : "semantic tree not loaded")
        )
      )
    );
  }

  function ReadGroup({ title, reads, runRead, loading }) {
    return h("div", { className: "iphone-group" },
      h("h3", null, title),
      h("div", { className: "iphone-actions" },
        reads.map(([key, label]) => h(Button, { key, onClick: () => runRead(key), disabled: loading }, label))
      )
    );
  }

  function ActionGroup({ title, actions, runAction, loading, confirm }) {
    return h("div", { className: "iphone-group" },
      h("h3", null, title),
      h("div", { className: "iphone-actions" },
        actions.map(([action, label]) => h(Button, { key: action, onClick: () => runAction(action), disabled: loading || !confirm }, label))
      )
    );
  }

  function IphoneDashboard() {
    const [overview, setOverview] = hooks.useState(null);
    const [detail, setDetail] = hooks.useState(null);
    const [error, setError] = hooks.useState("");
    const [loading, setLoading] = hooks.useState(false);
    const [confirm, setConfirm] = hooks.useState(false);
    const [udid, setUdid] = hooks.useState("");
    const [bundleId, setBundleId] = hooks.useState("");
    const [url, setUrl] = hooks.useState("");

    async function refresh(initial) {
      setLoading(true);
      setError("");
      try {
        const query = udid ? `?udid=${encodeURIComponent(udid)}` : "";
        const data = await api(`/overview${query}`);
        setOverview(data);
        if (initial || !detail) setDetail(data);
      } catch (err) {
        setError(err && err.message ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }

    hooks.useEffect(() => { refresh(true); }, []);

    async function runRead(readKey) {
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams();
        if (udid) params.set("udid", udid);
        params.set("limit", readKey === "tree" ? "80" : "20");
        const data = await api(`/read/${readKey}?${params.toString()}`);
        setDetail(data);
      } catch (err) {
        setError(err && err.message ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }

    async function runAction(action) {
      setLoading(true);
      setError("");
      try {
        const body = { action, confirm };
        if (udid) body.udid = udid;
        if (bundleId) body.bundle_id = bundleId;
        if (url) body.url = url;
        const data = await api("/quick-action", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        setDetail(data);
        await refresh(false);
      } catch (err) {
        setError(err && err.message ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }

    return h("div", { className: "iphone-dashboard" },
      h("div", { className: "iphone-hero" },
        h("div", null,
          h("p", { className: "iphone-eyebrow" }, "Hermes iPhone plugin"),
          h("h1", null, "Attached iPhone"),
          h("p", { className: "iphone-muted" }, "Current device status, screen context, traces, screenshots, and guarded quick actions.")
        ),
        h("div", { className: "iphone-hero-actions" },
          h(Button, { onClick: () => refresh(false), disabled: loading }, loading ? "Refreshing…" : "Refresh"),
          h(Badge, { className: overview && overview.ok ? "iphone-ok" : "iphone-warn" }, overview && overview.ok ? "dashboard live" : "loading")
        )
      ),
      overview ? h(OverviewCards, { overview }) : h(Card, null, h(CardContent, null, "Loading iPhone overview…")),
      h("div", { className: "iphone-workbench" },
        h(Card, null,
          h(CardHeader, null, h(CardTitle, null, "Target & inputs")),
          h(CardContent, null,
            h(TextInput, { label: "UDID override", value: udid, setValue: setUdid, placeholder: "optional attached device UDID" }),
            h(TextInput, { label: "Bundle ID", value: bundleId, setValue: setBundleId, placeholder: "com.apple.MobileSMS" }),
            h(TextInput, { label: "URL", value: url, setValue: setUrl, placeholder: "https://example.com" }),
            h("label", { className: "iphone-confirm" },
              h("input", { type: "checkbox", checked: confirm, onChange: (event) => setConfirm(event.target.checked) }),
              h("span", null, "I confirm this iPhone quick action")
            ),
            h("p", { className: "iphone-muted" }, "Message-send prepare/confirm tools are intentionally not exposed here; use Hermes chat approval for text sends.")
          )
        ),
        h(Card, null,
          h(CardHeader, null, h(CardTitle, null, "Reads")),
          h(CardContent, null, READ_GROUPS.map(([title, reads]) => h(ReadGroup, { key: title, title, reads, runRead, loading })))
        ),
        h(Card, null,
          h(CardHeader, null, h(CardTitle, null, "Guarded quick actions")),
          h(CardContent, null, ACTION_GROUPS.map(([title, actions]) => h(ActionGroup, { key: title, title, actions, runAction, loading, confirm })))
        ),
        error ? h(Card, { className: "iphone-error-card" }, h(CardContent, null, h("p", { className: "iphone-error" }, error))) : null,
        h(Card, { className: "iphone-payload-card" },
          h(CardHeader, null, h(CardTitle, null, "Redacted last payload")),
          h(CardContent, null, detail ? h(JsonBlock, { data: detail }) : h("p", { className: "iphone-muted" }, "Run a read or confirmed action to inspect plugin output."))
        )
      )
    );
  }

  function HeaderWidget() {
    return h("span", { className: "iphone-header-pill", title: "iPhone dashboard plugin installed" }, "iPhone");
  }

  window.__HERMES_PLUGINS__.register("hermes-iphone-plugin", IphoneDashboard);
  window.__HERMES_PLUGINS__.registerSlot("hermes-iphone-plugin", "header-right", HeaderWidget);
})();
