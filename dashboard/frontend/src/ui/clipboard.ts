export interface ClipboardDependencies {
  writeText?: (value: string) => Promise<void>;
  fallbackCopy: (value: string) => boolean;
}

/** Prefer the async Clipboard API, then fall back to a temporary selection. */
export async function copyText(value: string, dependencies: ClipboardDependencies = browserClipboard()): Promise<boolean> {
  if (dependencies.writeText) {
    try {
      await dependencies.writeText(value);
      return true;
    } catch {
      // Permission and insecure-context failures still get the local fallback.
    }
  }
  return dependencies.fallbackCopy(value);
}

function browserClipboard(): ClipboardDependencies {
  return {
    writeText: navigator.clipboard?.writeText
      ? (value) => navigator.clipboard.writeText(value)
      : undefined,
    fallbackCopy: legacyCopy,
  };
}

function legacyCopy(value: string): boolean {
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.readOnly = true;
  textarea.setAttribute("aria-hidden", "true");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  textarea.style.pointerEvents = "none";
  document.body.append(textarea);
  textarea.select();
  try {
    return typeof document.execCommand === "function" && document.execCommand("copy");
  } catch {
    return false;
  } finally {
    textarea.remove();
  }
}
