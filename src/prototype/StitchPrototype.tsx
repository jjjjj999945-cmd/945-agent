import { useEffect, useMemo, useState } from "react";
import { screens, type StitchScreen } from "./screens";
import { extractBody } from "./stitchDom";

function getCurrentScreen(): StitchScreen {
  const path = window.location.pathname.replace(/^\/+/, "").replace(/^prototype\/?/, "");
  const match = screens.find((screen) => screen.route === path);
  return match ?? screens[0];
}

function prototypeHref(screen: StitchScreen) {
  return screen.route ? `/prototype/${screen.route}` : "/prototype";
}

export function StitchPrototype() {
  const [current, setCurrent] = useState<StitchScreen>(() => getCurrentScreen());
  const [html, setHtml] = useState("");
  const [bodyClass, setBodyClass] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const onPopState = () => setCurrent(getCurrentScreen());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    setLoading(true);
    fetch(`/stitch-reference/${current.folder}/screen.html`)
      .then((response) => {
        if (!response.ok) throw new Error(`Unable to load ${current.title}`);
        return response.text();
      })
      .then((source) => {
        const extracted = extractBody(source, current.folder);
        setBodyClass(extracted.bodyClass);
        setHtml(extracted.html);
      })
      .finally(() => setLoading(false));
  }, [current]);

  useEffect(() => {
    document.title = `${current.shortTitle} - 945`;
    document.documentElement.className = "light";
    document.body.className = bodyClass;
    return () => {
      document.body.className = "";
    };
  }, [current, bodyClass]);

  useEffect(() => {
    const root = document.querySelector(".stitch-screen");
    if (!root) return;

    const onClick = (event: Event) => {
      const target = event.target as HTMLElement;
      const anchor = target.closest("a") as HTMLAnchorElement | null;
      if (anchor && anchor.getAttribute("href") === "#") {
        event.preventDefault();
        const title = anchor.getAttribute("title");
        const icon = iconText(anchor);
        const destination = title ? routeForTitle(title) : routeForIcon(icon) ?? routeForText(actionText(anchor));
        if (destination) {
          if (destination.route === current.route) showToast(`${destination.shortTitle} is already open.`);
          else navigate(destination);
        }
        else if (unavailableSectionForText(actionText(anchor))) {
          selectPeerControl(anchor);
          showToast(`${unavailableSectionForText(actionText(anchor))} screen is not included in this Stitch export yet.`);
        }
        else {
          selectPeerControl(anchor);
          showToast("Prototype section selected.");
        }
      }

      const button = target.closest("button");
      if (button) {
        event.preventDefault();
        const title = button.getAttribute("title");
        const icon = iconText(button);
        const destination = title ? routeForTitle(title) : routeForIcon(icon);
        if (destination) {
          if (destination.route === current.route) showToast(`${destination.shortTitle} is already open.`);
          else navigate(destination);
          return;
        }
        button.classList.add("stitch-pressed");
        window.setTimeout(() => button.classList.remove("stitch-pressed"), 220);
        handlePrototypeAction(button, current, navigate, showToast);
      }
    };

    const onChange = (event: Event) => {
      const target = event.target as HTMLElement;
      if (target.matches("input, textarea, select")) handlePrototypeInput(target, showToast);
    };

    const onInput = (event: Event) => {
      const target = event.target as HTMLElement;
      if (target.matches("input[type='range']")) handlePrototypeInput(target, showToast, false);
    };

    root.addEventListener("click", onClick);
    root.addEventListener("change", onChange);
    root.addEventListener("input", onInput);
    return () => {
      root.removeEventListener("click", onClick);
      root.removeEventListener("change", onChange);
      root.removeEventListener("input", onInput);
    };
  }, [current, html]);

  const nav = useMemo(() => screens.filter((screen) => screen.primary), []);

  function navigate(screen: StitchScreen) {
    window.history.pushState({}, "", prototypeHref(screen));
    setCurrent(screen);
  }

  function showToast(message: string) {
    let toast = document.querySelector(".prototype-toast") as HTMLElement | null;
    if (!toast) {
      toast = document.createElement("div");
      toast.className = "prototype-toast";
      toast.setAttribute("role", "status");
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("prototype-toast-visible");
    window.clearTimeout((showToast as unknown as { timeout?: number }).timeout);
    (showToast as unknown as { timeout?: number }).timeout = window.setTimeout(() => {
      toast?.classList.remove("prototype-toast-visible");
    }, 2400);
  }

  return (
    <>
      <div className="prototype-reference-badge">Stitch reference</div>
      <div className="prototype-switcher" aria-label="Stitch prototype screens">
        <select
          value={current.route}
          onChange={(event) => {
            const next = screens.find((screen) => screen.route === event.target.value);
            if (next) navigate(next);
          }}
        >
          {screens.map((screen) => (
            <option value={screen.route} key={screen.route}>
              {screen.index}. {screen.shortTitle}
            </option>
          ))}
        </select>
        <div className="prototype-tabs">
          {nav.map((screen) => (
            <button
              key={screen.route}
              className={screen.route === current.route ? "active" : ""}
              onClick={() => navigate(screen)}
            >
              {screen.navLabel}
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <div className="loading-screen">Loading Stitch screen...</div>
      ) : (
        <div className="stitch-screen" dangerouslySetInnerHTML={{ __html: html }} />
      )}
    </>
  );
}

function routeForTitle(title: string) {
  const normalized = title.toLowerCase();
  if (normalized.includes("today")) return screens[0];
  if (normalized.includes("workout")) return screens[1];
  if (normalized.includes("diet")) return screens[5];
  if (normalized.includes("advice")) return screens[9];
  if (normalized.includes("metrics")) return screens[3];
  if (normalized.includes("agent")) return screens[7];
  if (normalized.includes("settings")) return screens[2];
  if (normalized.includes("profile")) return screens[8];
  return undefined;
}

function routeForIcon(icon: string) {
  if (icon === "calendar_today") return screens[0];
  if (icon === "fitness_center") return screens[1];
  if (icon === "restaurant") return screens[5];
  if (icon === "monitoring") return screens[3];
  if (icon === "auto_awesome") return screens[9];
  if (icon === "smart_toy") return screens[7];
  if (icon === "settings") return screens[2];
  if (icon === "account_circle") return screens[8];
  return undefined;
}

function routeForText(text: string) {
  const normalized = text.toLowerCase();
  if (normalized.includes("dashboard")) return screens[0];
  if (normalized.includes("workout")) return screens[1];
  if (normalized.includes("diet") || normalized.includes("meal") || normalized.includes("nutrition")) return screens[5];
  if (normalized.includes("analytics") || normalized.includes("summary")) return screens[3];
  if (normalized.includes("settings")) return screens[2];
  return undefined;
}

function unavailableSectionForText(text: string) {
  const normalized = text.toLowerCase();
  if (normalized.includes("schedule")) return "Schedule";
  if (normalized.includes("body") || normalized.includes("metrics")) return "Body data";
  return undefined;
}

function handlePrototypeAction(
  button: HTMLButtonElement,
  current: StitchScreen,
  navigate: (screen: StitchScreen) => void,
  showToast: (message: string) => void
) {
  if (button.disabled || button.className.includes("cursor-not-allowed")) {
    showToast("This control is disabled in the current prototype state.");
    return;
  }

  const label = actionText(button);
  const normalized = label.toLowerCase();
  const icon = iconText(button);

  if (normalized.includes("sync agent") || icon === "sync") {
    markButtonDone(button, "Synced");
    showToast("Agent context synced with the latest demo data.");
    return;
  }

  if (icon === "notifications") {
    showToast("No new notifications.");
    return;
  }

  if (icon === "history_edu" || normalized.includes("history")) {
    showToast("History panel opened for this prototype state.");
    button.classList.toggle("bg-primary/10");
    button.classList.toggle("text-primary");
    return;
  }

  if (icon === "more_vert") {
    selectPeerControl(button);
    showToast("More actions menu opened for this prototype.");
    return;
  }

  if (icon === "play_circle") {
    const row = button.closest(".flex, div") as HTMLElement | null;
    const playIcon = button.querySelector(".material-symbols-outlined");
    if (playIcon) playIcon.textContent = "check_circle";
    row?.classList.add("prototype-complete");
    showToast("Exercise marked complete.");
    return;
  }

  if (normalized.includes("start session") || normalized.includes("begin")) {
    markButtonDone(button, "Session Active");
    showToast("Workout session started. Exercise rows can now be marked complete.");
    return;
  }

  if (normalized === "finish" || icon === "stop_circle" || normalized.includes("finish workout") || normalized.includes("complete workout") || normalized.includes("save workout")) {
    markButtonDone(button, "Workout Saved");
    showToast("Workout log saved to the demo timeline.");
    return;
  }

  if (normalized.includes("start exercise") || icon === "add_circle") {
    markButtonDone(button, current.route.includes("agent") ? "Added" : "Exercise Added");
    showToast(current.route.includes("agent") ? "Draft item added." : "Exercise set added to the workout.");
    return;
  }

  if (icon === "check") {
    const row = button.closest(".flex, .rounded-2xl, .rounded-3xl, div") as HTMLElement | null;
    row?.classList.add("prototype-complete");
    markButtonDone(button, "Done");
    showToast(current.route.includes("diet") ? "Meal item confirmed." : "Set confirmed.");
    return;
  }

  if (icon === "edit" || normalized.includes("modify draft")) {
    const card = button.closest(".glass-card, .glass-panel, .rounded-2xl, .rounded-3xl, div") as HTMLElement | null;
    card?.classList.toggle("prototype-editing");
    showToast(normalized.includes("modify draft") ? "Draft is ready for edits." : "Edit mode toggled.");
    return;
  }

  if (normalized.includes("log meal") || normalized.includes("add meal") || normalized.includes("manual entry")) {
    markButtonDone(button, "Meal Logged");
    showToast("Meal logged in the local demo state.");
    return;
  }

  if (normalized.includes("log water")) {
    markButtonDone(button, "Water Logged");
    showToast("Hydration entry added.");
    return;
  }

  if (normalized.includes("quick log") || normalized.includes("save check") || normalized.includes("save daily")) {
    markButtonDone(button, "Check-in Saved");
    showToast("Daily check-in saved.");
    return;
  }

  if (normalized.includes("apply") || normalized.includes("accept") || normalized.includes("approve") || normalized.includes("confirm adjustment")) {
    markButtonDone(button, "Applied");
    showToast("Recommendation applied to the demo plan.");
    return;
  }

  if (normalized.includes("keep original") || normalized.includes("keep current")) {
    markButtonDone(button, "Kept");
    showToast("Current plan kept unchanged.");
    return;
  }

  if (normalized.includes("dismiss") || normalized.includes("cancel")) {
    const card = button.closest(".glass-card, .glass-panel, .rounded-2xl, .rounded-3xl") as HTMLElement | null;
    if (card && normalized.includes("dismiss")) card.classList.add("prototype-dismissed");
    showToast(normalized.includes("cancel") ? "Edits cancelled." : "Recommendation dismissed.");
    return;
  }

  if (normalized.includes("review details")) {
    const destination = screens.find((screen) => screen.route === "ai-adjustment");
    if (destination) navigate(destination);
    return;
  }

  if (normalized.includes("save changes") || normalized === "save") {
    markButtonDone(button, "Saved");
    showToast("Preferences saved locally.");
    return;
  }

  if (normalized.includes("export")) {
    markButtonDone(button, "Exported");
    showToast("Demo export prepared.");
    return;
  }

  if (normalized.includes("push to garmin")) {
    markButtonDone(button, "Pushed");
    showToast("Draft pushed to the simulated Garmin connection.");
    return;
  }

  if (icon === "send" || icon === "arrow_upward" || normalized.includes("send")) {
    sendPrototypeMessage(button, showToast);
    return;
  }

  if (icon === "mic") {
    button.classList.toggle("text-primary");
    showToast("Voice capture toggled for the prototype.");
    return;
  }

  if (icon === "chevron_left" || icon === "chevron_right") {
    const label = current.route.includes("weekly") ? "week" : "day";
    showToast(icon === "chevron_left" ? `Moved to previous ${label}.` : `Moved to next ${label}.`);
    return;
  }

  if (button.textContent?.match(/\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b/i)) {
    selectSiblingButton(button);
    showToast("Date selected.");
    return;
  }

  if (current.route === "onboarding" || normalized.includes("initialize") || normalized.includes("continue")) {
    markButtonDone(button, "Profile Ready");
    showToast("Demo profile initialized.");
    window.setTimeout(() => navigate(screens[0]), 500);
    return;
  }

  if (icon) {
    button.classList.toggle("text-primary");
    showToast("Prototype state updated.");
    return;
  }

  showToast("Prototype action registered.");
}

function handlePrototypeInput(element: HTMLElement, showToast: (message: string) => void, announce = true) {
  if (element instanceof HTMLInputElement) {
    if (element.type === "checkbox") {
      element.closest("label, .flex, .glass-card, .glass-panel")?.classList.toggle("prototype-selected", element.checked);
      if (announce) showToast(element.checked ? "Preference enabled." : "Preference disabled.");
      return;
    }

    if (element.type === "radio") {
      const name = element.name;
      if (name) {
        document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`).forEach((radio) => {
          radio.closest("label, .flex, .glass-card, .glass-panel")?.classList.toggle("prototype-selected", radio === element);
        });
      }
      if (announce) showToast("Option selected.");
      return;
    }

    if (element.type === "range") {
      element.closest(".glass-card, .glass-panel, .flex, div")?.classList.add("prototype-selected");
      if (announce) showToast(`Value set to ${element.value}.`);
      return;
    }
  }

  element.classList.add("prototype-field-edited");
  if (announce) showToast("Field updated.");
}

function actionText(element: HTMLElement) {
  const clone = element.cloneNode(true) as HTMLElement;
  clone.querySelectorAll(".material-symbols-outlined").forEach((node) => node.remove());
  return (clone.textContent ?? "").replace(/\s+/g, " ").trim();
}

function iconText(element: HTMLElement) {
  return element.querySelector(".material-symbols-outlined")?.textContent?.trim() ?? "";
}

function markButtonDone(button: HTMLButtonElement, label: string) {
  button.classList.add("prototype-done");
  const icon = button.querySelector(".material-symbols-outlined");
  if (icon) icon.textContent = "check";
  const textNodes = [...button.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE);
  if (textNodes.length) {
    textNodes[textNodes.length - 1].textContent = ` ${label}`;
  } else if (!button.querySelector(".material-symbols-outlined")) {
    button.textContent = label;
  } else {
    button.append(` ${label}`);
  }
}

function selectSiblingButton(button: HTMLButtonElement) {
  const parent = button.parentElement;
  if (!parent) return;
  parent.querySelectorAll("button").forEach((item) => {
    item.classList.remove("bg-primary", "text-white", "shadow-[0_4px_15px_rgba(0,65,220,0.2)]");
  });
  button.classList.add("bg-primary", "text-white", "shadow-[0_4px_15px_rgba(0,65,220,0.2)]");
}

function selectPeerControl(element: HTMLElement) {
  const parent = element.parentElement;
  if (!parent) return;
  parent.querySelectorAll("button, a").forEach((item) => item.classList.remove("prototype-selected"));
  element.classList.add("prototype-selected");
}

function sendPrototypeMessage(button: HTMLButtonElement, showToast: (message: string) => void) {
  const container = button.closest("div");
  const input = (container?.querySelector("input") ?? document.querySelector("input[placeholder*='Ask'], input[placeholder*='Type']")) as HTMLInputElement | null;
  const raw = input?.value.trim();
  const message = raw || "Can you review today's plan?";
  if (input) input.value = "";

  const bubble = document.createElement("div");
  bubble.className = "prototype-message";
  bubble.innerHTML = `
    <div class="prototype-message-user">${escapeHtml(message)}</div>
    <div class="prototype-message-agent">Agent noted this and prepared a structured demo response. Confirm before any plan or log changes are saved.</div>
  `;

  const inputShell = button.closest(".sticky, .border-t, .glass-card, .glass-panel");
  if (inputShell?.parentElement) {
    inputShell.parentElement.insertBefore(bubble, inputShell);
  } else {
    const main = document.querySelector("main");
    (main ?? document.body).appendChild(bubble);
  }
  showToast("Message sent to Agent.");
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
